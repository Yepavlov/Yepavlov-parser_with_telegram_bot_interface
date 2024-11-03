import asyncio

from parsers.work_ua_parser import WorkUaParser
from sorter.candidate_sorter import CandidateSorter


async def main():
    criteria = {"position": "Django"}

    parser = WorkUaParser(criteria)

    await parser.fetch_initial_resumes()

    await parser.fetch_all_resumes()

    desired_skills = ["Python", "Django", "REST API", "Знання принципів ООП"]

    sorter = CandidateSorter(parser.resumes, desired_skills)

    sorted_candidates = sorter.sort_candidates()

    for resume, score in sorted_candidates:
        print(f"Score: {score}, Resume: {resume}")

    # print(worker.available_filters)
    # # filter = "від " + str(worker.available_filters['salary_expectations']["від"].index('10 000 грн (99)'))
    # filter = 'Без досвіду'
    # print(filter)
    # html_content_with_search = await worker.fetch_resumes_based_on_filters(filter)
    # print("---------------------")
    # print(html_content_with_search)


asyncio.run(main())
