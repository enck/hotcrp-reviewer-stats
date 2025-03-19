# hotcrp-reviewer-stats

This is a script to process [HotCRP](https://github.com/kohler/hotcrp/) logs to identify the performance of program committee members.
It was originally written for [IEEE S&P 2025](https://www.ieee-security.org/TC/SP2025/) by PC co-chair [William Enck](https://github.com/enck) with the goal of identifying the top five reviewers, which were given complementary registration for the symposium.
However, the output `.csc` file can be also used to identify under-performing PC members that should not be invited to PCs in subsequent years.
Specifically, the `sum_days_late` column is the aggregate days late a reviewer is on submitting reviews.
A low number of comments also indicates an inactive PC member.

Note that the script is heavily influence by the structure of the IEEE S&P 2025 review structure.
Specifically, there were 
(1) multiple submission cycles,
(2) two rounds of review within each cycle,
(3) an interactive rebuttal where reviewers were expected to interact with authors, 
(4) all papers were shepherded to determine the final meta-review text, and
(5) only "primary reviewers" assigned to papers.

There are several known limitations (mostly due to information available in logs):
- There is no clear way to determine which comments were author-visible
- If the shepherd is changed, there is double shepherd counting for that paper

## Downloading Files

Two files from each HotCRP instance are needed:
- [prefix]-users.csv: Users -> Program committee -> selected all, Download: "Names and emails"
- [prefix]-log.csv: Action Log -> Download

## Output Format

The script output is a `.csv` file with the following columns:

- **full_name:** The reviewer's full name
- **email:** The reviewer's email address
- **num_assigned_reviews:** The total number of reviews assigned across all cycles
- **num_completed_reviews:** The number of reviews they completed across all cycles
- **all_on_time:** A Boolean ('Y' / 'N') if all of their reviews were completed by assigned deadlines
- **sum_days_late:** The Aggregate days late on reviews for each deadline, across all cycles. If one day late on two papers, the sum is 2 days.
- **num_comments:** The total number of comments across all cycles
- **num_comments_r1_disc:** The number of coments during the R1 discussion, across all cycles.
- **num_comments_r2_disc:** The number of comments during the R2 discussion, across all cycles.
- **num_comments_rebuttal:** The number of comments during the rebuttal, across all cycles
- **num_shepherd:** The number of papers shepherded by the reviewer, across all cycles
- **num_comments_after_notification:** The number of comments after the decision notification, across all cycles (shows shepherding activity)

## Configuration

A sample multi-cycle configuration is in `config.toml`.
The config file specifies timestamps for each cycle.
The timestamp format is the same format used by HotCRP for the log file.
Choose the most appropriate timezone offset for each deadline.
For example, Samoa time makes sense for submission deadlines, but it may not makes sense for the other deadlines.

```toml
[general]
conference_name = "IEEE S&P 2025"

[[cycles]]
cycle_number = 1
log_file = "sp2025c1-log.csv"
reviewers_file = "sp2025c1-users.csv"

# Using Samoa time for deadlines. Eastern time for discussion periods
[cycles.timestamps] # "%Y-%m-%d %H:%M:%S %z"
submission = "2024-06-06 23:59:59 -1100"
round1_deadline = "2024-07-10 23:59:59 -1100"
round1_discussion_start = "2024-07-11 00:00:00 -0400"
round1_discussion_end = "2024-07-19 23:59:59 -0400"
round2_deadline = "2024-08-09 23:59:59 -1100"
round2_discussion_start = "2024-08-12 00:00:00 -0400"
round2_discussion_end = "2024-09-08 23:59:59 -0400"
rebuttal_discussion_start = "2024-08-19 00:00:00 -0400" 
rebuttal_discussion_end = "2024-08-30 23:59:59 -0400"
acceptance = "2024-09-09 12:00:00 -0400"
camera_ready = "2024-10-18 23:59:59 -1100"

[[cycles]]
cycle_number = 2
log_file = "sp2025c2-log.csv"
reviewers_file = "sp2025c2-users.csv"

# Using Samoa time for deadlines. Eastern time for discussion periods
[cycles.timestamps] # "%Y-%m-%d %H:%M:%S %z"
submission = "2024-11-14 23:59:59 -1100"
round1_deadline = "2025-01-10 23:59:59 -1100"
round1_discussion_start = "2025-01-11 00:00:00 -0500"
round1_discussion_end = "2025-01-17 23:59:59 -0500"
round2_deadline = "2025-02-07 23:59:59 -1100"
round2_discussion_start = "2025-02-10 00:00:00 -0500"
round2_discussion_end = "2025-03-09 23:59:59 -0500"
rebuttal_discussion_start = "2025-02-17 00:00:00 -0400" 
rebuttal_discussion_end = "2025-02-28 23:59:59 -0400"
acceptance = "2025-03-10 12:00:00 -0400"
camera_ready = "2025-04-18 23:59:59 -1100"
```

## Running the script

The script print a csv file to `stdout`.
There may be some warnings printed to `stderr`, so it good just redirect `stdout` to a file.

```sh
% ./reviewer-stats.py > stats.csv
```

Possible warnings include:
- Missing users: This may happen if you assigned reviews to an individual and then removed them from the PC. These should be safe to ignore.
- New HotCRP log actions. You can add these to `process_log()` so that you know you have caught everything important.

## Development Notes

### Logfile order

The HotCRP logfile is in reverse chronological order.
While I considered preprocessing the logfile to make the processing cleaner, that would require doing that step every time.
Logfiles can be fairly big, and with a little care, it was possible to process the logs in reverse.
