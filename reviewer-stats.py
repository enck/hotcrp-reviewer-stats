#!/usr/bin/env python3
"""
~~~~~~~~~~~~~~~~

Copyright 2025 North Carolina State University

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice, this permission notice, and the non-endorsement notice below shall be included in all copies or substantial portions of the Software.

The names “North Carolina State University”, “NCSU” and any trade‐name, personal name,
trademark, trade device, service mark, symbol, image, icon, or any abbreviation, contraction or
simulation thereof owned by North Carolina State University must not be used to endorse or promote products derived from this software without prior written permission.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

~~~~~~~~~~~~~~~~
"""

"""
reviewer-stats.py: Generate PC statistics from HotCRP logs

This script was originally written by William Enck <whenck@ncsu.edu> for
processing HotCRP logs for IEEE S&P 2025.

Usage:
    reviewer-stats.py > output.csv

Configuration: config.toml

--- Sample Configuration ---

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

----------------------------

"""

import csv
import sys
import re
import tomllib
from datetime import datetime

# Used for both HotCRP logs and TOML config
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S %z"

# Note: the paper number is acutally "[cyclenum]-[papernum]" to handle multiple cycles
# This is a helper function for sorting that
def paper_sort_key(item):
    first, second = map(int, item.split('-'))
    return (first, second)

class Reviewer:
    def __init__(self, first_name, last_name, email):
        self.full_name = '{} {}'.format(first_name, last_name)
        self.email = email
        self.reviews = {} # map of paper -> Review object
        self.comments = [] # array of timestamps when comments made
        self.shepherd = [] # array of shepherded papers. WARNING: cannot handle shepherding changes

    def assign_review(self, paper, timestamp, round_deadline, cycle_end):
        if paper in self.reviews:
            self.reviews[paper].assign_update(timestamp, round_deadline)
        else:
            self.reviews[paper] = self.Review(paper, True, timestamp, round_deadline, cycle_end, None)

    def unassign_review(self, paper, timestamp, round_deadline, cycle_end):
        if paper in self.reviews:
            self.reviews[paper].unassign_update(timestamp, round_deadline)
        else:
            self.reviews[paper] = self.Review(paper, False, timestamp, round_deadline, cycle_end, None)

    def paper_assignment(self):
        papers = [paper for paper in self.reviews if self.reviews[paper].is_assigned() ]
        return sorted(papers, key=paper_sort_key)

    def review_submitted(self, paper, cycle_end, timestamp):
        if paper in self.paper_assignment():
            self.reviews[paper].submitted_update(timestamp)
        else:
            # We don't yet know when or if the paper was assigned
            self.reviews[paper] = self.Review(paper, False, None, None, cycle_end, timestamp)

    def has_reviews(self):
        for paper in self.reviews:
            if self.reviews[paper].is_assigned():
                return True

        return False
        
    def all_reviews_on_time(self):
        on_time = True
        for paper in self.reviews:
            if not self.reviews[paper].submitted_on_time():
                on_time = False

        return on_time

    def sum_days_late(self):
        days = 0
        for paper in self.reviews:
            if not self.reviews[paper].submitted_on_time():
                late = self.reviews[paper].time_late()
                if late != None:
                    days += late.days

        return days


    def completed_reviews(self):
        return [paper for paper in self.reviews if self.reviews[paper].is_submitted() ]

    def add_comment(self, timestamp):
        self.comments.append(timestamp)

    def has_comments(self):
        if len(self.comments) > 0:
            return True

        return False

    def set_shepherd(self, paper, timestamp):
        # Ignoring timestamp for now. Cannot handle multiple set-shepherd events for the same paper
        self.shepherd.append(paper)

    def shepherd_assignments(self):
        return self.shepherd

    # start_ts or end_ts == None provides infinite bounds
    def num_comments(self, start_ts=None, end_ts=None):
        count = 0

        for time in self.comments:
            if (start_ts == None or start_ts <= time) and (end_ts == None or time <= end_ts):
                count += 1

        return count

    def print_reviewer_info_header():
        print("full_name,email,num_assigned_reviews,num_completed_reviews,all_on_time,sum_days_late,num_comments,num_comments_r1_disc,num_comments_r2_disc,num_comments_rebuttal,num_shepherd,num_comments_after_notification")

    def print_reviewer_info(self, config):
        r1_disc_com = 0 # R1 discusson comments
        r2_disc_com = 0 # R2 discussion comments
        rb_disc_com = 0 # Rebuttal discussion comments
        after_not_com = 0 # After notification comments (i.e., shepherding)

        # Talley comments for each cycle
        for cycle in config["cycles"]:
            timestamps = cycle["timestamps"]
                
            r1_disc_start = datetime.strptime(timestamps["round1_discussion_start"], TIMESTAMP_FORMAT)
            r1_disc_end = datetime.strptime(timestamps["round1_discussion_end"], TIMESTAMP_FORMAT)
            r1_disc_com += self.num_comments(r1_disc_start, r1_disc_end)

            r2_disc_start = datetime.strptime(timestamps["round2_discussion_start"], TIMESTAMP_FORMAT)
            r2_disc_end = datetime.strptime(timestamps["round2_discussion_end"], TIMESTAMP_FORMAT)
            r2_disc_com += self.num_comments(r2_disc_start, r2_disc_end)

            rb_disc_start = datetime.strptime(timestamps["rebuttal_discussion_start"], TIMESTAMP_FORMAT)
            rb_disc_end = datetime.strptime(timestamps["rebuttal_discussion_end"], TIMESTAMP_FORMAT)
            rb_disc_com += self.num_comments(rb_disc_start, rb_disc_end)

            paper_not = datetime.strptime(timestamps["acceptance"], TIMESTAMP_FORMAT)
            cam_ready = datetime.strptime(timestamps["camera_ready"], TIMESTAMP_FORMAT)
            after_not_com += self.num_comments(paper_not, cam_ready)

        #papers = ', '.join(self.paper_assignment())
        print('{},{},{},{},{},{},{},{},{},{},{},{}'.format(
            self.full_name,
            self.email,
            len(self.paper_assignment()),
            len(self.completed_reviews()),
            'Y' if self.all_reviews_on_time() else 'N',
            self.sum_days_late(),
            self.num_comments(),
            r1_disc_com,
            r2_disc_com,
            rb_disc_com,
            len(self.shepherd_assignments()),
            after_not_com,
            ))

    class Review:
        # Created either when review assigned / unassigned or when review is submitted
        # - Note: Logs are read in reverse order
        def __init__(self, paper, assigned, time_assigned, time_due, cycle_end, time_submitted):
            self.paper = paper
            self.assigned = assigned # true or false
            self.time_assigned = time_assigned
            self.time_due = time_due
            self.cycle_end = cycle_end
            self.time_submitted = time_submitted

        def assign_update(self, timestamp, deadline):
            # The latest action in the log is the correct one
            if self.time_assigned == None or self.time_assigned < timestamp:
                self.assigned = True
                self.time_assigned = timestamp
                self.time_due = deadline

        def unassign_update(self, timestamp, deadline):
            # The latest action in the log is the correct one
            if self.time_assigned == None or self.time_assigned < timestamp:
                self.assigned = False
                self.time_assigned = timestamp
                self.time_due = deadline

        def submitted_update(self, timestamp):
            # Store the earliest time it the paper was submitted
            if self.time_submitted == None or self.time_submitted > timestamp:
                self.time_submitted = timestamp

        def is_assigned(self):
            return self.assigned

        def is_submitted(self):
            return (self.time_submitted != None)

        def submitted_on_time(self):
            # Reviews that were unassigned are always on-time
            if self.assigned == False:
                return True

            # Reviews that were never submitted are not on-time
            if self.time_submitted == None:
                return False

            if self.time_submitted <= self.time_due:
                return True

            # Don't penalize late review assignments
            if self.time_assigned > self.time_due:
                return True

            return False

        # Returns 0 if not late
        def time_late(self):
            if self.submitted_on_time():
                return None

            # Never submitted
            if self.time_submitted == None:
                return self.cycle_end - self.time_due

            return self.time_submitted - self.time_due


def load_reviewers(filename):
    reviewers = {} # Map reviewer email to Reviewer object

    with open(filename, 'r', encoding="utf8") as f:
        reviewers_csv = csv.reader(f)
        for row in reviewers_csv:
            if row[0] == 'first':
                # head line, skip. We assume the following data format
                assert(row[1] == 'last' and row[2] == 'email')
                continue

            first_name, last_name, email = row[0], row[1], row[2]

            if not email in reviewers:
                reviewers[email] = Reviewer(first_name, last_name, email)

    return reviewers

def process_log(reviewers, logfile, cycle_number, timestamps):
    with open(logfile, 'r', encoding="utf8") as f:
        log_csv = csv.reader(f)
        for row in log_csv:
            if row[0] == 'date':
                # head line, skip. We assume the following data format
                assert(row[2] == 'email' and row[4] == 'affected_email' and
                       row[6] == 'paper' and row[7] == 'action')
                continue

            date, email, affected_email, paper, action = row[0], row[2], row[4], row[6], row[7]
            timestamp = datetime.strptime(date, TIMESTAMP_FORMAT)
            cycle = cycle_number
            cycle_paper = "{}-{}".format(cycle, paper)
            cycle_end = datetime.strptime(timestamps["acceptance"], TIMESTAMP_FORMAT)

            if action == "Assigned primary review (round R1)":
                round_deadline = datetime.strptime(timestamps["round1_deadline"], TIMESTAMP_FORMAT)
                # add the assigned review to reviewer
                if affected_email in reviewers:
                    reviewers[affected_email].assign_review(cycle_paper, timestamp, round_deadline, cycle_end)
                else:
                    print("Warning: could not find {} for Cycle {} R1 assignment #{}".format(affected_email, cycle, paper), file=sys.stderr)

            elif action == "Assigned primary review (round R2)":
                round_deadline = datetime.strptime(timestamps["round2_deadline"], TIMESTAMP_FORMAT)
                # add the assigned review to reviewer
                if affected_email in reviewers:
                    reviewers[affected_email].assign_review(cycle_paper, timestamp, round_deadline, cycle_end)
                else:
                    print("Warning: could not find {} for Cycle {} R2 assignment #{}".format(affected_email, cycle, paper), file=sys.stderr)

            elif action == "Removed primary review (round R1)":
                round_deadline = datetime.strptime(timestamps["round1_deadline"], TIMESTAMP_FORMAT)
                # remove the assigned review to reviewer
                if affected_email in reviewers:
                    reviewers[affected_email].unassign_review(cycle_paper, timestamp, round_deadline, cycle_end)
                else:
                    print("Warning: could not find {} for Cycle {} R1 removed assignment #{}".format(affected_email, cycle, paper), file=sys.stderr)

            elif action == "Removed primary review (round R2)":
                round_deadline = datetime.strptime(timestamps["round2_deadline"], TIMESTAMP_FORMAT)
                # remove the assigned review to reviewer
                if affected_email in reviewers:
                    reviewers[affected_email].unassign_review(cycle_paper, timestamp, round_deadline, cycle_end)
                else:
                    print("Warning: could not find {} for Cycle {} R2 removed assignment #{}".format(affected_email, cycle, paper), file=sys.stderr)

            elif re.match(r"^Review \d+ submitted: ", action):
                # mark review as submitted
                # Question: should we capture the number of words in the review?
                if email in reviewers:
                    reviewers[email].review_submitted(cycle_paper, cycle_end, timestamp)
                else:
                    print("Warning: could not find {} for Cycle {} review submitted #{}".format(email, cycle, paper), file=sys.stderr)

            elif re.match(r"^Review \d+ edited draft: ", action):
                # Not tracking review editing for now.
                # - This is before the review is submitted, so definitely ignore
                pass

            elif re.match(r"^Review \d+ edited: ", action):
                # Not tracking review editing for now.
                # - Is editing reviews after rebuttal useful?
                pass

            elif re.match(r"^Review \d+ deleted", action):
                # Not tracking review deletion for now.
                pass

            elif re.match(r"^Set shepherd", action):
                # Reviewer was added as a shepherd for a paper
                if affected_email in reviewers:
                    reviewers[affected_email].set_shepherd(cycle_paper, timestamp)
                else:
                    print("Warning: could not find {} for Cycle {} set shepherd on #{}".format(affected_email, cycle, paper), file=sys.stderr)

            elif re.match(r"^Unsubmitted primary review", action):
                pass

            elif re.match(r"^Response", action):
                # Responses are added by authors. No need to track
                pass

            elif re.match(r"^Comment \d+ (on submission )?submitted", action):
                # mark comment activity
                # - Note: It does not seem possible to extract if a commit is author-visible
                if email in reviewers:
                    reviewers[email].add_comment(timestamp)
                #else:
                    # Authors make comments, so don't worry about this case
                    #print("Warning: could not find {} for comment added #{}".format(email, paper), file=sys.stderr)

            elif re.match(r"^Comment \d+ (on submission )?edited draft", action):
                # Not tracking comment editing for now.
                pass

            elif re.match(r"^Comment \d+ (on submission )?deleted", action):
                # Not tracking comment deletion. Only looking for activity.
                pass

            elif re.match(r"^Assigned meta review", action):
                pass

            elif re.match(r"^Removed meta review", action):
                pass

            elif re.match(r"^Changed meta review", action):
                pass

            elif re.match(r"^Unsubmitted meta review", action):
                pass

            elif re.match(r"^Download", action):
                pass

            elif re.match(r"^Password", action):
                pass

            elif re.match(r"^Account", action):
                pass

            elif re.match(r"^Paper", action):
                pass

            elif re.match(r"^Sent mail", action):
                pass

            elif re.match(r"^Sending mail", action):
                pass

            elif re.match(r"^Tag", action):
                pass

            elif re.match(r"^Set decision", action):
                pass

            elif re.match(r"^Settings edited:", action):
                pass

            elif re.match(r"^(Set|Clear) lead", action):
                pass

            else:
                print("Warning: Cycle {} unknown action [{}]".format(cycle, action), file=sys.stderr)
                #pass



if __name__ == '__main__':

    with open("config.toml", "rb") as f:
        config = tomllib.load(f)

    # First, get the union of all reviewers in the cycles
    reviewers = {}
    for cycle in config["cycles"]:
        reviewers_file = cycle["reviewers_file"]
        cycle_reviewers = load_reviewers(reviewers_file)
        reviewers.update(cycle_reviewers)

    # Next, process the log files for each cycle
    for cycle in config["cycles"]:
        cycle_number = cycle["cycle_number"]
        log_file = cycle["log_file"]
        timestamps = cycle["timestamps"]

        process_log(reviewers, log_file, cycle_number, timestamps)

    # Finally, print all of the information
    Reviewer.print_reviewer_info_header()

    for r in reviewers:
        reviewers[r].print_reviewer_info(config)
