#!/usr/bin/env python3
import os
import re
import sys
from datetime import date, datetime

def log(str):
  sys.stderr.write(str)
  sys.stderr.write("\n")


class Tag:
  tag_re = re.compile(r"""
    (?P<prefix> [@+] )
    (?P<key> \S+? )
    (: (?P<value> \S+ ) )?
    \b
  """, re.VERBOSE)

  @classmethod
  def parse_all(cls, raw):
    prefix_to_cls = { Context.prefix: Context, Project.prefix: Project }
    tags = set()
    for m in cls.tag_re.finditer(raw):
      prefix = m.group("prefix")
      key = m.group("key")
      value = m.group("value")
      tag = prefix_to_cls[prefix](key, value)
      tags.add(tag)
    return tags

  def __init__(self, prefix, key, value):
    self.prefix = prefix
    self.key = key
    self.value = value
    self.raw = prefix + key + (value if value else "")

  def __repr__(self):
    return self.raw

  def __eq__(self, other):
    return self.raw.__eq__(other.raw)

  def __hash__(self):
    return self.raw.__hash__()


class Project(Tag):
  prefix = "+"

  def __init__(self, key, value):
    Tag.__init__(self, self.prefix, key, value)


class Context(Tag):
  prefix = "@"

  def __init__(self, key, value):
    Tag.__init__(self, self.prefix, key, value)


class Task:
  task_re = re.compile(r"""^
    ( x \s+ (?P<complete> [0-9]{4}-[0-9]{2}-[0-9]{2} ) \s+ )?
    ( \( (?P<priority> [A-Z] ) \) \s+ )?
    ( (?P<create> [0-9]{4}-[0-9]{2}-[0-9]{2} ) \s+ )?
    (?P<title> .*? )
  $""", re.VERBOSE)

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
    self.tags = Tag.parse_all(title)

  def __repr__(self):
    return self.line


def get_tasks(path):
  with open(path, "r") as f:
    return {i + 1: Task.parse(line.rstrip("\r\n")) for i, line in enumerate(f)}

tasks = get_tasks(os.environ["TODO_FILE"])
print(tasks)


