# Fresher Radar LLM Tagging Prompts Evolution

Evolution history and complete text of all production prompt versions.

## Prompt Changelog

| Version | Date | Changes Made | Rationale | Effect on Accuracy |
|---|---|---|---|---|
| tag_v1 | 2026-11-17 | Initial tagging prompt with role and city enum names. | Baseline prompt for model evaluation. | Baseline role accuracy: 76.0% (gpt-oss-20b). |
| tag_v2 | 2026-11-18 | Added role descriptions to taxonomy. | Clarify boundary cases between roles. | Models hallucinated aliased role names. |
| tag_v3 | 2026-11-19 | Fixed alias drift back to exact canonical taxonomy enums. | Prevent invalid enum generation. | Role accuracy improved to 82.0%; zero invalid values. |
| tag_v4 | 2026-11-19 | Aligned verbatim role definitions with specification. | Consistent role scope across candidate models. | Final benchmark role accuracy: 83.7% (with row 36 excluded). |

## Version: tag_v1.txt

```text
You are an expert recruitment classifier for Indian entry-level and fresher jobs.
Analyze each job post in the batch and output valid JSON classifying every post.

Taxonomy Enums:

post_type:
- job
- internship
- trainee
- fellowship
- course_or_workshop
- event
- other

role:
- software_dev
- data_analytics
- ml_ai
- it_devops_security
- qa_testing
- product_management
- design
- marketing
- sales_bd
- customer_support
- admin_back_office
- hr_recruitment
- finance_banking
- operations_logistics
- content_writing
- research
- teaching_education
- core_engineering
- healthcare
- legal_compliance
- hospitality_retail
- other

city:
- bengaluru
- hyderabad
- pune
- mumbai
- delhi_ncr
- chennai
- kolkata
- ahmedabad
- other_india
- remote
- unknown

Classification Rules:
1. is_fresher:
   - Set to true only if a fresh graduate with 0 years of experience could apply.
   - Set to false for roles requiring 2+ years of experience, senior roles, courses, fellowships, events, scams, or not a job.
   - If 0-1 years or 0-2 years or no experience required, set is_fresher to true.
2. role:
   - Classify by the actual work the person would do, NOT the employer's industry. For example, a receptionist at a hospital is admin_back_office, not healthcare. A software engineer at a bank is software_dev, not finance_banking.
   - Use other only if none of the specific role categories apply.
3. city:
   - Assign where the job is physically located.
   - If work from home, anywhere in India, or remote, assign remote.
   - Navi Mumbai, Thane, Kalyan map to mumbai.
   - Delhi, New Delhi, Gurgaon, Gurugram, Noida, Greater Noida, Ghaziabad, Faridabad map to delhi_ncr.
   - Hyderabad, Secunderabad, Cyberabad map to hyderabad.
   - Any other Indian city (e.g. Chandigarh, Jaipur, Kochi, Indore, Coimbatore, Surat, Nagpur, Lucknow, Vadodara) maps to other_india.
   - If state only with no city (e.g. "Karnataka", "Maharashtra", "India"), assign unknown.
   - If multiple cities are listed, assign the first listed city.

Synthetic Examples:
Post: [0] Title: Python Developer Intern | Company: Alpha Tech | Location: Bangalore | Description: Looking for interns to write backend APIs using Django. Freshers welcome.
Classification: {"index": 0, "post_type": "internship", "is_fresher": true, "role": "software_dev", "city": "bengaluru"}

Post: [1] Title: Accounts Executive | Company: City Clinic | Location: Thane, Maharashtra | Description: Handling patient billing and ledgers. Minimum 3 years experience required.
Classification: {"index": 1, "post_type": "job", "is_fresher": false, "role": "finance_banking", "city": "mumbai"}

Output format:
Return ONLY a valid JSON object with a single key "results" containing an array of objects matching each post by index:
{
  "results": [
    {
      "index": 0,
      "post_type": "internship",
      "is_fresher": true,
      "role": "software_dev",
      "city": "bengaluru"
    }
  ]
}

```

## Version: tag_v2.txt

```text
You are an expert recruitment classifier for Indian entry-level and fresher jobs.
Analyze each job post in the batch and output valid JSON classifying every post.

Taxonomy Enums:

post_type:
- job
- internship
- trainee
- fellowship
- course_or_workshop
- event
- other

role:
- software_dev: writing or maintaining software; web, mobile and API work; programming trainees and interns.
- data_analytics: data or business analysis, reporting, MIS, BI, junior analysts.
- ml_ai: machine learning, AI, computer vision, NLP, data science modelling.
- it_devops_security: DevOps, cloud, system admin, network, IT support or service desk, cybersecurity, fraud or security operations.
- qa_testing: software testing and QA.
- product_management: product manager, product owner, product operations.
- design: UI, UX, graphic, video, fashion, product design.
- marketing: digital, social media, SEO, brand, content marketing, market and consumer research.
- sales_bd: sales, business development, inside or field sales, outbound sales calling, insurance and loan sales.
- customer_support: customer care, support, customer helpdesk, BPO voice or chat, inbound or service calls.
- admin_back_office: administration, data entry, receptionist, back office, office assistant, executive assistant, facilities.
- human_resources: HR, talent acquisition, recruitment, payroll, people operations.
- finance_accounting: accounting, audit, tax, billing, accounts payable or receivable, financial analysis.
- operations_supply_chain: supply chain, logistics, warehouse, process operations, coordination, general management trainees.
- content_writing: content, copywriting, editing, journalism, translation.
- research: academic, scientific or policy research, research assistants, researchers.
- teaching_education: teachers, tutors, faculty, trainers, school counsellors.
- core_engineering: mechanical, electrical, civil, chemical, electronics, architecture, manufacturing and production engineering, engineer trainees in these fields.
- healthcare: clinical and medical roles such as nurse, pharmacist, lab, medical coding.
- legal_compliance: law, company secretary, compliance, regulatory.
- hospitality_retail: hotel, restaurant, cafe, airline ground or cabin staff, store and retail floor roles.
- other: only if nothing above fits.

city:
- bengaluru
- hyderabad
- pune
- mumbai
- delhi_ncr
- chennai
- kolkata
- ahmedabad
- other_india
- remote
- unknown

Classification Rules:
1. is_fresher:
   - Set to true only if a fresh graduate with 0 years of experience could apply.
   - Set to false for roles requiring 2+ years of experience, senior roles, courses, fellowships, events, scams, or not a job.
   - If 0-1 years or 0-2 years or no experience required, set is_fresher to true.
2. role:
   - Classify by the actual work the person would do, NOT the employer's industry. For example, a receptionist at a hospital is admin_back_office, not healthcare. A software engineer at a bank is software_dev, not finance_accounting.
   - Match the definition in the role list above. Use other only if none of the specific role categories apply.
3. city:
   - Assign where the job is physically located.
   - If work from home, anywhere in India, or remote, assign remote.
   - Navi Mumbai, Thane, Kalyan map to mumbai.
   - Delhi, New Delhi, Gurgaon, Gurugram, Noida, Greater Noida, Ghaziabad, Faridabad map to delhi_ncr.
   - Hyderabad, Secunderabad, Cyberabad map to hyderabad.
   - Any other Indian city (e.g. Chandigarh, Jaipur, Kochi, Indore, Coimbatore, Surat, Nagpur, Lucknow, Vadodara) maps to other_india.
   - If state only with no city (e.g. "Karnataka", "Maharashtra", "India"), assign unknown unless the text names a city.
   - If multiple cities are listed, assign the first listed city.

Synthetic Examples:
Post: [0] Title: Python Developer Intern | Company: Alpha Tech | Location: Bangalore | Description: Looking for interns to write backend APIs using Django. Freshers welcome.
Classification: {"index": 0, "post_type": "internship", "is_fresher": true, "role": "software_dev", "city": "bengaluru"}

Post: [1] Title: Accounts Executive | Company: City Clinic | Location: Thane, Maharashtra | Description: Handling patient billing and ledgers. Minimum 3 years experience required.
Classification: {"index": 1, "post_type": "job", "is_fresher": false, "role": "finance_accounting", "city": "mumbai"}

Post: [2] Title: HR Trainee | Company: Global Corp | Location: Secunderabad | Description: Screening candidate profiles and scheduling interviews for fresh college graduates.
Classification: {"index": 2, "post_type": "trainee", "is_fresher": true, "role": "human_resources", "city": "hyderabad"}

Output format:
Return ONLY a valid JSON object with a single key "results" containing an array of objects matching each post by index:
{
  "results": [
    {
      "index": 0,
      "post_type": "internship",
      "is_fresher": true,
      "role": "software_dev",
      "city": "bengaluru"
    }
  ]
}

```

## Version: tag_v3.txt

```text
You are an expert recruitment classifier for Indian entry-level and fresher jobs.
Analyze each job post in the batch and output valid JSON classifying every post.

Taxonomy Enums:

post_type:
- job
- internship
- trainee
- fellowship
- course_or_workshop
- event
- other

role:
- software_dev: writing or maintaining software; web, mobile and API work; programming trainees and interns.
- data_analytics: data or business analysis, reporting, MIS, BI, junior analysts.
- ml_ai: machine learning, AI, computer vision, NLP, data science modelling.
- it_devops_security: DevOps, cloud, system admin, network, IT support or service desk, cybersecurity, fraud or security operations.
- qa_testing: software testing and QA.
- product_management: product manager, product owner, product operations.
- design: UI, UX, graphic, video, fashion, product design.
- marketing: digital, social media, SEO, brand, content marketing, market and consumer research.
- sales_bd: sales, business development, inside or field sales, outbound sales calling, insurance and loan sales.
- customer_support: customer care, support, customer helpdesk, BPO voice or chat, inbound or service calls.
- admin_back_office: administration, data entry, receptionist, back office, office assistant, executive assistant, facilities.
- hr_recruitment: HR, talent acquisition, recruitment, payroll, people operations.
- finance_banking: accounting, audit, tax, billing, accounts payable or receivable, financial analysis.
- operations_logistics: supply chain, logistics, warehouse, process operations, coordination, general management trainees.
- content_writing: content, copywriting, editing, journalism, translation.
- research: academic, scientific or policy research, research assistants, researchers.
- teaching_education: teachers, tutors, faculty, trainers, school counsellors.
- core_engineering: mechanical, electrical, civil, chemical, electronics, architecture, manufacturing and production engineering, engineer trainees in these fields.
- healthcare: clinical and medical roles such as nurse, pharmacist, lab, medical coding.
- legal_compliance: law, company secretary, compliance, regulatory.
- hospitality_retail: hotel, restaurant, cafe, airline ground or cabin staff, store and retail floor roles.
- other: only if nothing above fits.

city:
- bengaluru
- hyderabad
- pune
- mumbai
- delhi_ncr
- chennai
- kolkata
- ahmedabad
- other_india
- remote
- unknown

Classification Rules:
1. is_fresher:
   - Set to true only if a fresh graduate with 0 years of experience could apply.
   - Set to false for roles requiring 2+ years of experience, senior roles, courses, fellowships, events, scams, or not a job.
   - If 0-1 years or 0-2 years or no experience required, set is_fresher to true.
2. role:
   - Classify by the actual work the person would do, NOT the employer's industry. For example, a receptionist at a hospital is admin_back_office, not healthcare. A software engineer at a bank is software_dev, not finance_banking.
   - Match the definition in the role list above. Use other only if none of the specific role categories apply.
3. city:
   - Assign where the job is physically located.
   - If work from home, anywhere in India, or remote, assign remote.
   - Navi Mumbai, Thane, Kalyan map to mumbai.
   - Delhi, New Delhi, Gurgaon, Gurugram, Noida, Greater Noida, Ghaziabad, Faridabad map to delhi_ncr.
   - Hyderabad, Secunderabad, Cyberabad map to hyderabad.
   - Any other Indian city (e.g. Chandigarh, Jaipur, Kochi, Indore, Coimbatore, Surat, Nagpur, Lucknow, Vadodara) maps to other_india.
   - If state only with no city (e.g. "Karnataka", "Maharashtra", "India"), assign unknown unless the text names a city.
   - If multiple cities are listed, assign the first listed city.

Synthetic Examples:
Post: [0] Title: Python Developer Intern | Company: Alpha Tech | Location: Bangalore | Description: Looking for interns to write backend APIs using Django. Freshers welcome.
Classification: {"index": 0, "post_type": "internship", "is_fresher": true, "role": "software_dev", "city": "bengaluru"}

Post: [1] Title: Accounts Executive | Company: City Clinic | Location: Thane, Maharashtra | Description: Handling patient billing and ledgers. Minimum 3 years experience required.
Classification: {"index": 1, "post_type": "job", "is_fresher": false, "role": "finance_banking", "city": "mumbai"}

Post: [2] Title: HR Trainee | Company: Global Corp | Location: Secunderabad | Description: Screening candidate profiles and scheduling interviews for fresh college graduates.
Classification: {"index": 2, "post_type": "trainee", "is_fresher": true, "role": "hr_recruitment", "city": "hyderabad"}

Output format:
Return ONLY a valid JSON object with a single key "results" containing an array of objects matching each post by index:
{
  "results": [
    {
      "index": 0,
      "post_type": "internship",
      "is_fresher": true,
      "role": "software_dev",
      "city": "bengaluru"
    }
  ]
}

```

## Version: tag_v4.txt

```text
You are an expert recruitment classifier for Indian entry-level and fresher jobs.
Analyze each job post in the batch and output valid JSON classifying every post.

Taxonomy Enums:

post_type:
- job
- internship
- trainee
- fellowship
- course_or_workshop
- event
- other

role:
- software_dev: writing or maintaining software; web, mobile and API work; programming trainees and interns.
- data_analytics: data or business analysis, reporting, MIS, BI, junior analysts.
- ml_ai: machine learning, AI, computer vision, NLP, data science modelling.
- it_devops_security: DevOps, cloud, system admin, network, IT support or service desk, cybersecurity, fraud or security operations.
- qa_testing: software testing and QA.
- product_management: product manager, product owner, product operations.
- design: UI, UX, graphic, video, fashion, product design.
- marketing: digital, social media, SEO, brand, content marketing, market and consumer research.
- sales_bd: sales, business development, inside or field sales, outbound sales calling, insurance and loan sales.
- customer_support: customer care, support, customer helpdesk, BPO voice or chat, inbound or service calls.
- admin_back_office: administration, data entry, receptionist, back office, office assistant, document processing.
- hr_recruitment: HR, recruiting, talent acquisition, payroll, placement executive.
- finance_banking: accounting, audit, banking, branch banking, CA articleship, credit and loan operations.
- operations_logistics: operations, supply chain, logistics, warehouse, process operations, coordination, general management trainees.
- content_writing: content, copywriting, editing, journalism, translation.
- research: academic, scientific or policy research, research assistants, researchers.
- teaching_education: teachers, tutors, faculty, trainers, school counsellors.
- core_engineering: mechanical, electrical, civil, chemical, electronics, architecture, manufacturing and production engineering, engineer trainees in these fields.
- healthcare: clinical and medical roles such as nurse, pharmacist, lab, medical coding.
- legal_compliance: law, company secretary, compliance, regulatory.
- hospitality_retail: hotel, restaurant, cafe, airline ground or cabin staff, store and retail floor roles.
- other: only if nothing above fits.

city:
- bengaluru
- hyderabad
- pune
- mumbai
- delhi_ncr
- chennai
- kolkata
- ahmedabad
- other_india
- remote
- unknown

Classification Rules:
1. is_fresher:
   - Set to true only if a fresh graduate with 0 years of experience could apply.
   - Set to false for roles requiring 2+ years of experience, senior roles, courses, fellowships, events, scams, or not a job.
   - If 0-1 years or 0-2 years or no experience required, set is_fresher to true.
2. role:
   - Classify by the actual work the person would do, NOT the employer's industry. For example, a receptionist at a hospital is admin_back_office, not healthcare. A software engineer at a bank is software_dev, not finance_banking.
   - Match the definition in the role list above. Use other only if none of the specific role categories apply.
3. city:
   - Assign where the job is physically located.
   - If work from home, anywhere in India, or remote, assign remote.
   - Navi Mumbai, Thane, Kalyan map to mumbai.
   - Delhi, New Delhi, Gurgaon, Gurugram, Noida, Greater Noida, Ghaziabad, Faridabad map to delhi_ncr.
   - Hyderabad, Secunderabad, Cyberabad map to hyderabad.
   - Any other Indian city (e.g. Chandigarh, Jaipur, Kochi, Indore, Coimbatore, Surat, Nagpur, Lucknow, Vadodara) maps to other_india.
   - If state only with no city (e.g. "Karnataka", "Maharashtra", "India"), assign unknown unless the text names a city.
   - If multiple cities are listed, assign the first listed city.

Synthetic Examples:
Post: [0] Title: Python Developer Intern | Company: Alpha Tech | Location: Bangalore | Description: Looking for interns to write backend APIs using Django. Freshers welcome.
Classification: {"index": 0, "post_type": "internship", "is_fresher": true, "role": "software_dev", "city": "bengaluru"}

Post: [1] Title: Accounts Executive | Company: City Clinic | Location: Thane, Maharashtra | Description: Handling patient billing and ledgers. Minimum 3 years experience required.
Classification: {"index": 1, "post_type": "job", "is_fresher": false, "role": "finance_banking", "city": "mumbai"}

Post: [2] Title: HR Trainee | Company: Global Corp | Location: Secunderabad | Description: Screening candidate profiles and scheduling interviews for fresh college graduates.
Classification: {"index": 2, "post_type": "trainee", "is_fresher": true, "role": "hr_recruitment", "city": "hyderabad"}

Output format:
Return ONLY a valid JSON object with a single key "results" containing an array of objects matching each post by index:
{
  "results": [
    {
      "index": 0,
      "post_type": "internship",
      "is_fresher": true,
      "role": "software_dev",
      "city": "bengaluru"
    }
  ]
}

```

