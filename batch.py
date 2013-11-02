#!/usr/bin/env python3
import os
import re
from datetime import date, datetime

class Item:
  item_re = re.compile(r"""^
    ( x \s+ (?P<complete> [0-9]{4}-[0-9]{2}-[0-9]{2} ) \s+ )?
    ( \( (?P<priority> [A-Z] ) \) \s+ )?
    ( (?P<create> [0-9]{4}-[0-9]{2}-[0-9]{2} ) \s+ )?
    ( (?P<title> .*? ) \s* )
  $""", re.VERBOSE)

  @staticmethod
  def parse_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d').date() if date_str is not None else None

  def __init__(self, line):
    self.line = line
    m = self.item_re.match(self.line)
    assert m is not None, "item_re should match all lines: %s" % line
    self.creation_date = self.parse_date(m.group("create"))
    self.completion_date = self.parse_date(m.group("complete"))
    self.priority = m.group("priority")
    self.title = m.group("title")

  def __repr__(self):
    return str((self.completion_date, self.priority, self.creation_date, self.title))


def get_items(path):
  with open(path, "r") as f:
    return {i + 1: Item(line.rstrip("\r\n")) for i, line in enumerate(f)}

items = get_items(os.environ["TODO_FILE"])
print(items)

