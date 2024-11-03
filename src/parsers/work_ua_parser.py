import asyncio
import logging
from typing import Dict, Any

import aiohttp
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)


class WorkUaParser:
    BASE_URL = "https://www.work.ua/resumes"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/115.0 Safari/537.36"
    }
    SKILLS_ELEMENTS = "ul.list-unstyled.my-0.flex.flex-wrap li.no-style.mr-sm.mt-sm"
    SALARY_ELEMENTS = "select#salaryfrom_selection>option"
    GENDER_ELEMENTS = "#gender_selection label span"
    EXPERIENCE_ELEMENTS = "#experience_selection li"
    LOCATION = {
        "Київ": "-kyiv",
        "Дніпро": "-dnipro",
        "Одеса": "-odesa",
        "Харків": "-kharkiv",
        "Львів": "-lviv",
        "Інші країни": "-other",
        "Дистанційно": "-remote",
    }
    GENDER = {
        "Чоловік": "86",
        "Жінка": "87",
    }
    SKILLS = {"Шукати будь-яке зі слів": "anyword=1"}
    EXPERIENCE = {
        "Без досвіду": "0",
        "До 1 року": "1",
        "Від 1 до 2 років": "164",
        "Від 2 до 5 років": "165",
        "Понад 5 років": "166",
    }
    SALARY = {
        "від": "salaryfrom=",
        "до": "salaryto=",
    }

    def __init__(self, criteria: Dict[str, Any]):
        self.criteria = criteria
        self.available_filters = {}
        self.resumes = {}

    def define_count_pages(self, html_content: str) -> int:
        soup = BeautifulSoup(html_content, "lxml")
        pagination_links = soup.select("ul.pagination.hidden-xs li")
        page_numbers = [int(li.text) for li in pagination_links if li.text.isdigit()]
        return max(page_numbers) if page_numbers else 1

    async def fetch_content_from_url(self, url: str) -> str:
        """Fetches content from a given URL with error handling."""
        try:
            async with aiohttp.ClientSession(headers=self.HEADERS) as session:
                async with session.get(url) as response:
                    response.raise_for_status()  # Raise an error for bad status
                    return await response.text()
        except Exception as e:
            logging.error(f"Error fetching {url}: {e}")
            return ""

    async def fetch_initial_resumes(self):
        """Fetches initial resumes and parses available filters."""
        position = "+".join(self.criteria["position"].split())
        url = f"{self.BASE_URL}-{position}/"
        html_content = await self.fetch_content_from_url(url)
        count_pages = self.define_count_pages(html_content)
        for page in range(1, count_pages + 1):
            page_url = f"{self.BASE_URL}-{position}/?page={page}"
            html_content = await self.fetch_content_from_url(page_url)
            if html_content:
                if page == 1:
                    self.available_filters = self.parse_filters(html_content)
                self.parse_resumes(html_content)

    async def fetch_resumes_based_on_filters(self, filters: str):
        """Fetches resumes based on provided filters."""
        position = "+".join(self.criteria["position"].split())
        filter_query = self.generate_filter_query(filters)
        if filter_query in self.LOCATION.values():
            url = f"{self.BASE_URL}{filter_query}-{position}/"
        else:
            url = f"{self.BASE_URL}-{position}/?{filter_query}"
        html_content = await self.fetch_content_from_url(url)
        if html_content:
            self.available_filters = self.parse_filters(html_content)
            return self.parse_resumes(html_content)
        return []

    def parse_filters(self, html_content: str) -> dict:
        """Parses available filters from the initial HTML content."""
        soup = BeautifulSoup(html_content, "lxml")
        salary_exp_filter = [option.text.strip() for option in soup.select(self.SALARY_ELEMENTS)]
        gender_elements = [span.get_text(strip=True) for span in soup.select(self.GENDER_ELEMENTS)]
        gender_filter = [f"{gender_elements[i - 1]} {gender_elements[i]}" for i in range(len(gender_elements))
                         if gender_elements[i].isdigit()]
        experience_fileter = [f"{item.select_one('span').get_text()} | {item.select('span')[1].get_text()}"
                              for item in soup.select(self.EXPERIENCE_ELEMENTS)]
        self.available_filters["salary_expectations"] = {"від": salary_exp_filter,
                                                         "до": salary_exp_filter, }
        self.available_filters["gender"] = gender_filter
        self.available_filters["experience"] = experience_fileter
        return self.available_filters

    def parse_resumes(self, html_content: str) -> dict:
        """Parses resumes from the HTML content."""
        soup = BeautifulSoup(html_content, "lxml")
        for resume in soup.select("div.card.card-hover.card-search"):
            title_tag = resume.select_one("h2.mt-0 a")
            if title_tag:
                job_title = title_tag.text.strip()
                job_link = "https://www.work.ua" + title_tag["href"]
                user_id = "".join([el for el in title_tag["href"].split("/") if el.isdigit()])
                self.resumes[user_id] = {"link": job_link,
                                         "title": job_title}
            info_tag = resume.select_one("p.mt-xs.mb-0:not(.h5)")
            if info_tag:
                info = " ".join(span.text.replace("\xa0", " ").strip() for span in info_tag.find_all("span"))
                self.resumes[user_id]["info"] = info.strip() if info else "N/A"
        return self.resumes

    async def parse_specific_resume(self, url: str) -> dict:
        """Fetches and parses the specific resume page for additional details."""
        html_content = await self.fetch_content_from_url(url)
        if html_content:
            return self.extract_resume_details(html_content)
        return {}

    def extract_resume_details(self, html_content: str) -> dict:
        """Extracts details like skills and languages from a resume page."""
        soup = BeautifulSoup(html_content, "lxml")
        skills = [span.text.strip() for span in
                  soup.select("ul.list-unstyled.my-0.flex.flex-wrap li.no-style.mr-sm.mt-sm span.ellipsis")]
        return {
            "skills": skills,
        }

    async def fetch_all_resumes(self):
        """Fetches all resumes and updates them with specific details."""
        tasks = [self.parse_specific_resume(resume_data["link"]) for resume_data in self.resumes.values()]
        resumes_details = await asyncio.gather(*tasks)
        for resume_id, resume_details in zip(self.resumes.keys(), resumes_details):
            self.resumes[resume_id].update(resume_details)

    def generate_filter_query(self, filters: str) -> str:
        """Generates query string based on selected filters."""
        query_params = []
        if filters in self.LOCATION:
            query_params.append(f"{self.LOCATION[filters]}")
        if filters.split()[0] in self.GENDER:
            query_params.append(f"gender={self.GENDER[filters.split()[0]]}")
        if filters.split("|")[0] in self.EXPERIENCE:
            query_params.append(f"experience={self.EXPERIENCE[filters.split('|')[0]]}")
        if filters.split()[0] in self.SALARY:
            condition, index = filters.split()[0], filters.split()[1]
            query_params.append(f"{self.SALARY[condition]}{index}")
        if filters in self.SKILLS:
            query_params.append(self.SKILLS[filters])
        return "&".join(query_params)
