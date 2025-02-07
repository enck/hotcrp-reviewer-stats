#!/usr/bin/env python3

import csv
import sys
import re
from datetime import datetime

R1_DEADLINE = datetime.strptime("2024-07-10 23:59:59 -0400", "%Y-%m-%d %H:%M:%S %z")
R2_DEADLINE = datetime.strptime("2024-08-09 23:59:59 -0400", "%Y-%m-%d %H:%M:%S %z")

R1_DISCUSSION = {
        'start': datetime.strptime("2024-07-10 23:59:59 -0400", "%Y-%m-%d %H:%M:%S %z"),
        'end': datetime.strptime("2024-07-19 23:59:59 -0400", "%Y-%m-%d %H:%M:%S %z")
        }

R2_DISCUSSION = {
        'start': datetime.strptime("2024-07-10 23:59:59 -0400", "%Y-%m-%d %H:%M:%S %z"),
        'end': datetime.strptime("2024-07-19 23:59:59 -0400", "%Y-%m-%d %H:%M:%S %z")
        }

REBUTTAL_DISCUSSION = {
        'start': datetime.strptime("2024-07-16 23:59:59 -0400", "%Y-%m-%d %H:%M:%S %z"),
        'end': datetime.strptime("2024-07-28 23:59:59 -0400", "%Y-%m-%d %H:%M:%S %z")
        }

class Reviewer:
    def __init__(self, first_name, last_name, email):
        self.full_name = '{} {}'.format(first_name, last_name)
        self.email = email
        self.reviews = {} # map of paper -> Review object
        self.comments = [] # array of timestamps when comments made

    def assign_r1_review(self, paper, timestamp):
        if paper in self.reviews:
            self.reviews[paper].assign_update(timestamp, R1_DEADLINE)
        else:
            self.reviews[paper] = self.Review(paper, True, timestamp, R1_DEADLINE, None)

    def unassign_r1_review(self, paper, timestamp):
        if paper in self.reviews:
            self.reviews[paper].unassign_update(timestamp, R1_DEADLINE)
        else:
            self.reviews[paper] = self.Review(paper, False, timestamp, R1_DEADLINE, None)

    def assign_r2_review(self, paper, timestamp):
        if paper in self.reviews:
            self.reviews[paper].assign_update(timestamp, R2_DEADLINE)
        else:
            self.reviews[paper] = self.Review(paper, True, timestamp, R2_DEADLINE, None)

    def unassign_r2_review(self, paper, timestamp):
        if paper in self.reviews:
            self.reviews[paper].unassign_update(timestamp, R2_DEADLINE)
        else:
            self.reviews[paper] = self.Review(paper, False, timestamp, R2_DEADLINE, None)

    def paper_assignment(self):
        papers = [paper for paper in self.reviews if self.reviews[paper].is_assigned() ]
        return sorted(papers, key=int)

    def review_submitted(self, paper, timestamp):
        if paper in self.paper_assignment():
            self.reviews[paper].submitted_update(timestamp)
        else:
            # We don't yet know when or if the paper was assigned
            self.reviews[paper] = self.Review(paper, False, None, None, timestamp)

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

    def add_comment(self, timestamp):
        self.comments.append(timestamp)

    def has_comments(self):
        if len(self.comments) > 0:
            return True

        return False

    def num_r1_discussion_comments(self):
        count = 0
        for time in self.comments:
            if R1_DISCUSSION['start'] <= time and time <= R1_DISCUSSION['end']:
                count += 1

        return count

    def num_r2_discussion_comments(self):
        count = 0
        for time in self.comments:
            if R2_DISCUSSION['start'] <= time and time <= R2_DISCUSSION['end']:
                count += 1

        return count

    def num_rebuttal_discussion_comments(self):
        count = 0
        for time in self.comments:
            if REBUTTAL_DISCUSSION['start'] <= time and time <= REBUTTAL_DISCUSSION['end']:
                count += 1

        return count

    def print_reviewer_info(self):
        # email, full_name, "paper, paper, ...", num_r1_comments, num_r2_comments, num_rebuttal_comments
        papers = ', '.join(self.paper_assignment())
        r1_comments = self.num_r1_discussion_comments()
        r2_comments = self.num_r2_discussion_comments()
        rebuttal_comments = self.num_rebuttal_discussion_comments()
        print('{},{},"{}",{},{},{}'.format(self.email, self.full_name, papers, r1_comments, r2_comments, rebuttal_comments))

    class Review:
        # Created either when review assigned / unassigned or when review is submitted
        # - Note: Logs are read in reverse order
        def __init__(self, paper, assigned, time_assigned, time_due, time_submitted):
            self.paper = paper
            self.assigned = assigned # true or false
            self.time_assigned = time_assigned
            self.time_due = time_due
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

        def is_assigned(self):
            return self.assigned

        def submitted_on_time(self):
            # Reviews that were unassigned are always on-time
            if self.assigned == False:
                return True

            # Reviews that were never submitted are not on-time
            if self.time_submitted == None:
                return False

            if self.time_submitted <= self.time_due:
                return True

            return False

        def submitted_update(self, timestamp):
            # Store the earliest time it the paper was submitted
            if self.time_submitted == None or self.time_submitted > timestamp:
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
                    reviewers[affected_email].assign_r1_review(paper, timestamp)
                else:
                    print("Warning: could not find {} for R1 assignment #{}".format(affected_email, paper), file=sys.stderr)

            elif action == "Assigned primary review (round R2)":
                # add the assigned review to reviewer
                if affected_email in reviewers:
                    reviewers[affected_email].assign_r2_review(paper, timestamp)
                else:
                    print("Warning: could not find {} for R2 assignment #{}".format(affected_email, paper), file=sys.stderr)

            elif action == "Removed primary review (round R1)":
                # remove the assigned review to reviewer
                if affected_email in reviewers:
                    reviewers[affected_email].unassign_r1_review(paper, timestamp)
                else:
                    print("Warning: could not find {} for R1 removed assignment #{}".format(affected_email, paper), file=sys.stderr)

            elif action == "Removed primary review (round R2)":
                # remove the assigned review to reviewer
                if affected_email in reviewers:
                    reviewers[affected_email].unassign_r2_review(paper, timestamp)
                else:
                    print("Warning: could not find {} for R2 removed assignment #{}".format(affected_email, paper), file=sys.stderr)

            elif re.match(r"^Review \d+ submitted: ", action):
                # mark review as submitted
                # Question: should we capture the number of words in the review?
                if email in reviewers:
                    reviewers[email].review_submitted(paper, timestamp)
                else:
                    print("Warning: could not find {} for review submitted #{}".format(email, paper), file=sys.stderr)

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

            elif re.match(r"^Set shepherd", action):
                pass

            elif re.match(r"^Settings edited:", action):
                pass

            elif re.match(r"^(Set|Clear) lead", action):
                pass

            else:
                print("Warning: unknown action [{}]".format(action), file=sys.stderr)
                #pass



if __name__ == '__main__':
    reviewers = load_reviewers("sp2025c1-users.csv")
    process_log(reviewers, "sp2025c1-log.csv")

    print("email, full_name, paper_assignment, num_r1_comments, num_r2_comments, num_rebuttal_comments")
    for r in reviewers:
        if reviewers[r].all_reviews_on_time() and reviewers[r].has_reviews():
            reviewers[r].print_reviewer_info()
