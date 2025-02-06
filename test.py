#!/usr/bin/env python3

import csv
import sys
import re
from datetime import datetime

R1_DEADLINE = datetime.strptime("2024-07-10 23:59:59 -0400", "%Y-%m-%d %H:%M:%S %z")
R2_DEADLINE = datetime.strptime("2024-08-09 23:59:59 -0400", "%Y-%m-%d %H:%M:%S %z")

class Reviewer:
    def __init__(self, first_name, last_name, email):
        self.full_name = '{} {}'.format(first_name, last_name)
        self.email = email
        self.reviews = {} # map of paper -> Review object
        self.reviews = {} # map of paper -> Review object

    def add_r1_review(self, paper, timestamp):
        if paper in self.reviews:
            self.reviews[paper].add_update(timestamp)
        else:
            self.reviews[paper] = self.Review(paper, True, timestamp, R1_DEADLINE)

    def del_r1_review(self, paper, timestamp):
        if paper in self.reviews:
            self.reviews[paper].del_update(timestamp)
        else:
            self.reviews[paper] = self.Review(paper, False, timestamp, R1_DEADLINE)

    def add_r2_review(self, paper, timestamp):
        if paper in self.reviews:
            self.reviews[paper].add_update(timestamp)
        else:
            self.reviews[paper] = self.Review(paper, True, timestamp, R2_DEADLINE)

    def del_r2_review(self, paper, timestamp):
        if paper in self.reviews:
            self.reviews[paper].del_update(timestamp)
        else:
            self.reviews[paper] = self.Review(paper, False, timestamp, R2_DEADLINE)

    def paper_assignment(self):
        papers = [paper for paper in self.reviews if self.reviews[paper].is_assigned() ]
        return sorted(papers, key=int)

    def review_submitted(self, paper, timestamp):
        if paper in self.paper_assignment():
            self.reviews[paper].submitted(timestamp)
        else:
            print("Warning: paper #{} submitted for {} <{}>, but never assigned".format(paper, self.full_name, self.email))
            papers = ', '.join(self.paper_assignment())
            print("->{}".format(papers))


    def print_reviewer_info(self):
        # email, full_name
        papers = ', '.join(self.paper_assignment())
        print('{},{},"{}"'.format(self.email, self.full_name, papers))

    class Review:
        def __init__(self, paper, assigned, time_assigned, time_due):
            self.paper = paper
            self.assigned = assigned # true or false
            self.time_assigned = time_assigned
            self.time_due = time_due
            self.time_submitted = None

        def add_update(self, timestamp):
            if self.time_assigned < timestamp:
                self.assigned = true
                self.time_assigned = timestamp

        def del_update(self, timestamp):
            if self.time_assigned < timestamp:
                self.assigned = false
                self.time_assigned = timestamp

        def is_assigned(self):
            return self.assigned

        def submitted(self, timestamp):
            # Only keep the earliest time it the paper was submitted
            if self.time_submitted == None:
                self.time_submitted = timestamp
            elif self.time_submitted > timestamp:
                self.time_submitted = timestamp

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

def process_log(reviewers, logfile):
    with open(logfile, 'r', encoding="utf8") as f:
        log_csv = csv.reader(f)
        for row in log_csv:
            if row[0] == 'date':
                # head line, skip. We assume the following data format
                assert(row[2] == 'email' and row[4] == 'affected_email' and
                       row[6] == 'paper' and row[7] == 'action')
                continue

            date, email, affected_email, paper, action = row[0], row[2], row[4], row[6], row[7]
            timestamp = datetime.strptime(date, "%Y-%m-%d %H:%M:%S %z")

            if action == "Assigned primary review (round R1)":
                # add the assigned review to reviewer
                if affected_email in reviewers:
                    reviewers[affected_email].add_r1_review(paper, timestamp)
                else:
                    print("Warning: could not find {}".format(affected_email))

            elif action == "Assigned primary review (round R2)":
                # add the assigned review to reviewer
                if affected_email in reviewers:
                    reviewers[affected_email].add_r2_review(paper, timestamp)
                else:
                    print("Warning: could not find {}".format(affected_email))

            elif action == "Removed primary review (round R1)":
                # remove the assigned review to reviewer
                if affected_email in reviewers:
                    reviewers[affected_email].del_r1_review(paper, timestamp)
                else:
                    print("Warning: could not find {}".format(affected_email))

            elif action == "Removed primary review (round R2)":
                # remove the assigned review to reviewer
                if affected_email in reviewers:
                    reviewers[affected_email].del_r2_review(paper, timestamp)
                else:
                    print("Warning: could not find {}".format(affected_email))

            elif re.match(r"^Review \d+ submitted: ", action):
                # mark review as submitted
                if email in reviewers:
                    reviewers[email].review_submitted(paper, timestamp)
                else:
                    print("Warning: could not find {}".format(affected_email))

            elif re.match(r"^Review \d+ edited draft: ", action):
                # mark review activity
                pass

            elif re.match(r"^Comment \d+ submitted", action):
                # mark comment activity
                pass

            elif re.match(r"^Comment \d+ edited draft:", action):
                # mark comment activity?
                pass

            else:
                # print unhandled case?
                pass



if __name__ == '__main__':
    reviewers = load_reviewers("sp2025c1-users.csv")
    process_log(reviewers, "sp2025c1-log.csv")

    for r in reviewers:
        reviewers[r].print_reviewer_info()
