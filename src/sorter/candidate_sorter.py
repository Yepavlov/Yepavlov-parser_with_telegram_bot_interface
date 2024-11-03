class CandidateSorter:
    def __init__(self, resumes: dict, desired_skills: list):
        """
        Initialize the CandidateSorter with resumes and the desired skills for scoring.
        :param resumes: A dictionary containing parsed resumes.
        :param desired_skills: A list of skills that are considered important for the position.
        """
        self.resumes = resumes
        self.desired_skills = desired_skills

    def score_resume(self, resume: dict) -> int:
        """
        Calculate the score of a single resume based on completeness and keyword matching.
        :param resume: A dictionary representing a candidate's resume data.
        :return: The calculated score for the resume.
        """
        score = 0
        if "link" in resume:
            score += 10  # Base score for completeness
        skills = resume.get("skills", [])
        skill_matches = set(skill.lower() for skill in skills) & set(desired_skill.lower() for desired_skill
                                                                     in self.desired_skills)
        score += len(skill_matches) * 3  # Each skill match adds 3 points
        if "info" in resume and resume["info"] != "N/A":
            score += 5  # Add points for additional information
        return score

    def sort_candidates(self):
        """
        Sort the candidates based on their scores in descending order.
        :return: A list of candidates sorted by relevance (highest score first).
        """
        scored_resumes = {user_id: self.score_resume(data) for user_id, data in self.resumes.items()}
        sorted_resumes = sorted(scored_resumes.items(), key=lambda item: item[1], reverse=True)
        return [(self.resumes[user_id], score) for user_id, score in sorted_resumes]
