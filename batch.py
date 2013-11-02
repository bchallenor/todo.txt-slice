#!/usr/bin/env python3
import os
import re
import sys
from datetime import date, datetime

def log(str):
  sys.stderr.write(str)
  sys.stderr.write("\n")


class Task:
  task_re = re.compile(r"""^
    ( x \s+ (?P<complete> [0-9]{4}-[0-9]{2}-[0-9]{2} ) \s+ )?
    ( \( (?P<priority> [A-Z] ) \) \s+ )?
    ( (?P<create> [0-9]{4}-[0-9]{2}-[0-9]{2} ) \s+ )?
    (?P<title> .*? )
  $""", re.VERBOSE)

  context_re = re.compile(r"@\S+")
  project_re = re.compile(r"\+\S+")

  @staticmethod
  def parse_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None

  @classmethod
  def parse(cls, line):
    m = cls.task_re.match(line)
    assert m is not None, "task_re should match all lines: %s" % line
    title = m.group("title")
    priority = m.group("priority")
    create_date = cls.parse_date(m.group("create"))
    complete_date = cls.parse_date(m.group("complete"))
    task = cls(title, priority, create_date, complete_date)
    assert task.line == line, "parsing should not lose information: <%s>" % line
    return task

  def __init__(self, title, priority, create_date = date.today(), complete_date = None):
    self.title = title
    self.priority = priority
    self.create_date = create_date
    self.complete_date = complete_date
    self.line = "".join([
      "x %s " % complete_date.isoformat() if complete_date else "",
      "(%s) " % priority if priority else "",
      "%s " % create_date.isoformat() if create_date else "",
      title
    ])
    self.contexts = set(self.context_re.findall(title))
    self.projects = set(self.project_re.findall(title))

  def __repr__(self):
    return self.line


def get_tasks(path):
  with open(path, "r") as f:
    return {i + 1: Task.parse(line.rstrip("\r\n")) for i, line in enumerate(f)}

tasks = get_tasks(os.environ["TODO_FILE"])
print(tasks)


