import re
from typing import Any

from pipeline.llm.base import (
    BaseLLMProvider,
    City,
    PostType,
    Role,
    TagResult,
    Usage,
)


class MockProvider(BaseLLMProvider):
    """Deterministic, offline provider for unit and dry tests."""

    def __init__(
        self,
        model: str = "mock",
        force_invalid_once: bool = False,
    ) -> None:
        super().__init__(model=model)
        self.force_invalid_once = force_invalid_once
        self._has_failed_once = False

    def _infer_role(self, title: str, desc: str) -> Role:
        text = f"{title} {desc}".lower()
        if re.search(
            r"\b(software|developer|frontend|backend|fullstack|sde|react|python|java|c\+\+)\b", text
        ):
            return Role.software_dev
        if re.search(r"\b(data analyst|analytics|sql|bi|tableau|power bi)\b", text):
            return Role.data_analytics
        if re.search(
            r"\b(machine learning|ai|nlp|computer vision|deep learning|data scientist)\b", text
        ):
            return Role.ml_ai
        if re.search(r"\b(qa|testing|quality assurance|automation tester)\b", text):
            return Role.qa_testing
        if re.search(r"\b(devops|cloud|aws|azure|docker|kubernetes|security)\b", text):
            return Role.it_devops_security
        if re.search(r"\b(product manager|product management|product associate)\b", text):
            return Role.product_management
        if re.search(r"\b(ui/ux|ui|ux|designer|graphic design)\b", text):
            return Role.design
        if re.search(r"\b(marketing|seo|content|social media)\b", text):
            return Role.marketing
        if re.search(r"\b(sales|business development|inside sales|bde)\b", text):
            return Role.sales_bd
        if re.search(r"\b(customer support|customer success|telecaller|counsellor)\b", text):
            return Role.customer_support
        if re.search(r"\b(back office|receptionist|office assistant|admin)\b", text):
            return Role.admin_back_office
        if re.search(r"\b(hr|recruiter|human resources|recruitment)\b", text):
            return Role.hr_recruitment
        if re.search(r"\b(finance|accounting|accountant|ca|audit|banking)\b", text):
            return Role.finance_banking
        if re.search(r"\b(operations|logistics|supply chain)\b", text):
            return Role.operations_logistics
        if re.search(r"\b(civil|mechanical|electrical|engineer|hardware)\b", text):
            return Role.core_engineering
        return Role.other

    def _infer_city(self, loc_text: str) -> City:
        loc = loc_text.lower()
        if "bangalore" in loc or "bengaluru" in loc:
            return City.bengaluru
        if "hyderabad" in loc:
            return City.hyderabad
        if "pune" in loc:
            return City.pune
        if "mumbai" in loc or "thane" in loc or "navi mumbai" in loc:
            return City.mumbai
        if "delhi" in loc or "noida" in loc or "gurgaon" in loc or "gurugram" in loc:
            return City.delhi_ncr
        if "chennai" in loc:
            return City.chennai
        if "kolkata" in loc:
            return City.kolkata
        if "ahmedabad" in loc:
            return City.ahmedabad
        if "remote" in loc or "wfh" in loc or "home" in loc:
            return City.remote
        if loc.strip():
            return City.other_india
        return City.unknown

    def tag_batch(
        self,
        posts: list[dict[str, Any]],
        prompt_version: str = "tag_v1",
    ) -> tuple[list[TagResult], Usage]:
        if self.force_invalid_once and not self._has_failed_once:
            self._has_failed_once = True
            raise ValueError("Malformed JSON response (simulated for retry test)")

        results: list[TagResult] = []
        input_tokens = 0
        output_tokens = len(posts) * 20

        for p in posts:
            idx = int(p.get("index", 0))
            title = str(p.get("title", ""))
            desc = str(p.get("description", ""))
            loc = str(p.get("location", ""))
            input_tokens += len(f"{title} {desc} {loc}".split()) + 25

            t_lower = title.lower()
            if "intern" in t_lower or "internship" in t_lower:
                pt = PostType.internship
                is_fresh = True
            elif "trainee" in t_lower or "apprentice" in t_lower:
                pt = PostType.trainee
                is_fresh = True
            elif "senior" in t_lower or "lead" in t_lower or "manager" in t_lower:
                pt = PostType.job
                is_fresh = False
            elif "course" in t_lower or "workshop" in t_lower:
                pt = PostType.course_or_workshop
                is_fresh = False
            else:
                pt = PostType.job
                is_fresh = True

            role = self._infer_role(title, desc)
            city = self._infer_city(loc)

            results.append(
                TagResult(
                    index=idx,
                    post_type=pt,
                    is_fresher=is_fresh,
                    role=role,
                    city=city,
                )
            )

        usage = Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=0,
            latency_ms=10,
            model=self.model,
            status="success",
        )
        return results, usage
