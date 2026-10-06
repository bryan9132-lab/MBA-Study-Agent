"""Loads sample course material into an empty database for the public demo.
All content below is original sample material written for the demo, not real course files."""
from datetime import datetime
from database import save_document

DOCS = [
    ("Microeconomics", "Syllabus", "MICRO_Syllabus_Fall2026.txt", """Microeconomics for Managers, Fall 2026 (sample)
Weekly pre-reading: assigned chapter is due before each Tuesday class (about 45 minutes each).
Problem Set 3 (game theory): due Monday, October 19, 11:59pm. Typically 2 to 3 hours.
Midterm exam: Tuesday, October 27, in class, 90 minutes, covers Weeks 1 to 7.
Problem Set 4 (pricing strategy): due Monday, November 16.
Group project, market entry analysis: proposal due November 2, final deck due December 7.
Final exam: Thursday, December 17, 3 hours, cumulative.
Grading: problem sets 25%, midterm 25%, group project 20%, final 30%."""),
    ("Microeconomics", "Class Notes", "Micro_Week6_notes.txt", """Week 6 notes: price discrimination
First degree: charge each customer their willingness to pay. Rare in practice, but dynamic pricing gets close.
Second degree: menu of options (bulk discounts, versions) so customers self-select.
Third degree: different prices for identifiable groups (student discounts, regional pricing). Requires preventing resale.
Key condition: firm has market power, can segment, and can limit arbitrage.
Example from class: airline fares differ by booking time and refundability, which sorts business from leisure travelers."""),
    ("Accounting", "Syllabus", "ACCT_Syllabus_Fall2026.txt", """Financial Accounting, Fall 2026 (sample)
Homework 4 (accrual adjustments): due Wednesday, October 14. Usually about 2.5 hours.
Homework 5 (inventory, FIFO vs LIFO): due Wednesday, October 28.
Midterm exam: Friday, October 30, closed book, one page of notes allowed.
Company analysis group assignment (buy, sell, or hold a public company): due November 20.
Final exam: Monday, December 14.
Pre-reading for every class is listed on the course page and takes about 30 to 60 minutes."""),
    ("Accounting", "Lecture Slides", "ACCT_L7_Revenue_Recognition.txt", """Lecture 7: revenue recognition
Five-step model: identify the contract, identify performance obligations, determine the price, allocate the price, recognize revenue when each obligation is satisfied.
Deferred revenue is a liability: cash received before the service is delivered.
Example: a $1,200 annual software subscription paid in January is recognized at $100 per month.
Common trap: recognizing the full amount at signing inflates current-period revenue."""),
    ("Leading People", "Syllabus", "LP_Syllabus_Fall2026.txt", """Leading People, Fall 2026 (sample)
Reflection paper 2 (a leader you worked for): due Friday, October 16, 1,000 words, about 2 hours.
Pre-reading case for each Thursday class, about 1 hour.
Team charter: due October 23.
Final team presentation on leading through change: week of December 1."""),
    ("Microeconomics", "Class Notes", "Granola - Week 7 game theory (sample).txt", """Lecture transcript summary (Granola, sample)
Professor opened with the prisoner's dilemma: two firms both cut prices even though both would earn more by holding prices high.
Nash equilibrium: each player's best response given what the other does. Neither wants to change alone.
Repeated games change the outcome: if firms compete every quarter, cooperation can hold because cheating today invites retaliation tomorrow.
Reminder from the professor: Problem Set 3 covers exactly these ideas and is due Monday; the midterm will include one game theory question."""),
    ("Data and Decisions", "Syllabus", "DD_Syllabus_Fall2026.txt", """Data and Decisions, Fall 2026 (sample)
Problem Set 5 (hypothesis testing): due Thursday, October 15. Usually about 3 hours.
Problem Set 6 (regression): due Thursday, October 29.
Midterm exam: Tuesday, November 3, open notes, Excel allowed.
Final project, a regression analysis on a dataset of your choice: due December 10."""),
    ("Data and Decisions", "Class Notes", "DD_Week5_notes.txt", """Week 5 notes: hypothesis testing
Null hypothesis is the default claim; we look for evidence against it.
p-value: probability of seeing data at least this extreme if the null is true. Small p-value means evidence against the null.
Type I error: rejecting a true null (false alarm). Type II error: missing a real effect.
Standard error of the mean = standard deviation / square root of n. Example: sd 10, n 100, SE = 1.
Rule of thumb: statistically significant does not always mean practically important."""),
]

def seed():
    """Add any sample documents that aren't in the database yet."""
    from database import get_all_filenames
    existing = get_all_filenames()
    now = datetime.now().isoformat()
    for course, category, filename, content in DOCS:
        if filename not in existing:
            save_document(filename, course, category, content, now)
