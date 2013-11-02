#!/usr/bin/env python3
import os
import re
from datetime import date, datetime

class Item:
  item_re = re.compile(r"""^
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
    m = cls.item_re.match(line)
    assert m is not None, "item_re should match all lines: %s" % line
    title = m.group("title")
    priority = m.group("priority")
    create_date = cls.parse_date(m.group("create"))
    complete_date = cls.parse_date(m.group("complete"))
    item = cls(title, priority, create_date, complete_date)
    assert item.line == line, "parsing should not lose information: <%s>" % line
    return item

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


def get_items(path):
  with open(path, "r") as f:
    return {i + 1: Item.parse(line.rstrip("\r\n")) for i, line in enumerate(f)}

items = get_items(os.environ["TODO_FILE"])
print(items)

