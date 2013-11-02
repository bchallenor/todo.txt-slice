#!/usr/bin/env python3
import os
import re
import sys
import subprocess
import string
import tempfile
from datetime import date, datetime

def log(str):
  sys.stderr.write(str)
  sys.stderr.write("\n")


editor_path = os.environ["EDITOR"]

todo_file_path = os.environ["TODO_FILE"]
date_on_add = os.environ["TODOTXT_DATE_ON_ADD"] == "1"
preserve_line_numbers = os.environ["TODOTXT_PRESERVE_LINE_NUMBERS"] == "1"


class Tag:
  tag_re = re.compile(r"""
    (
      (?P<prefix> [@+] )(?P<name> \S+ )
    |
      (?P<key> \S+? ) : (?P<value> \S+ )
    )
  """, re.VERBOSE)

  @staticmethod
  def handle_match(m):
    raw = m.group(0)
    prefix = m.group("prefix")
    name = m.group("name")
    key = m.group("key")
    value = m.group("value")
    if prefix:
      assert name, "name should be captured if prefix is captured: %s" % raw
      if prefix == "@":
        tag = ContextTag(name)
      elif prefix == "+":
        tag = ProjectTag(name)
      else:
        assert false, "unknown prefix: %s" % prefix
    else:
      assert key and value, "key and value should be captured if prefix is not: %s" % raw
      tag = KeyValueTag(key, value)
    assert tag.raw == raw, "parsing should not lose information: <%s>" % raw
    return tag

  @classmethod
  def parse(cls, raw):
    m = cls.tag_re.match(raw)
    if m and m.group(0) == raw: # check the whole string was matched
      return cls.handle_match(m)
    else:
      return None

  @classmethod
  def find_all(cls, raw):
    return {cls.handle_match(m) for m in cls.tag_re.finditer(raw)}

  def __init__(self, raw):
    self.raw = raw

  def __repr__(self):
    return self.raw

  def __eq__(self, other):
    return other is not None and self.raw.__eq__(other.raw)

  def __ne__(self, other):
    return not self.__eq__(other)

  def __hash__(self):
    return self.raw.__hash__()


class ContextTag(Tag):
  def __init__(self, name):
    self.name = name
    Tag.__init__(self, "@" + name)


class ProjectTag(Tag):
  def __init__(self, name):
    self.name = name
    Tag.__init__(self, "+" + name)


class KeyValueTag(Tag):
  def __init__(self, key, value):
    self.key = key
    self.value = value
    Tag.__init__(self, key + ":" + value)


class Task:
  task_re = re.compile(r"""
    ^
    ( x \s+ (?P<complete> [0-9]{4}-[0-9]{2}-[0-9]{2} ) \s+ )?
    ( \( (?P<priority> [A-Z] ) \) \s+ )?
    ( (?P<create> [0-9]{4}-[0-9]{2}-[0-9]{2} ) \s+ )?
    (?P<title> .*? )
    $
  """, re.VERBOSE)

  @staticmethod
  def parse_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None

  @classmethod
  def load_all(cls, path):
    with open(path, "r", encoding="utf-8") as f:
      tasks = {}
      for i, line in enumerate(f):
        id = i + 1
        line1 = line.rstrip("\r\n")
        if len(line1) > 0:
          tasks[id] = cls.parse(line1)
      return tasks

  @classmethod
  def save_all(cls, tasks, path):
    with open(path, "w", encoding="utf-8") as f:
      max_id = max(tasks.keys()) if len(tasks) > 0 else 0
      for id in range(1, max_id + 1):
        if id in tasks:
          task = tasks[id]
          f.write(task.line)
          f.write("\n")
        elif preserve_line_numbers:
          f.write("\n")

  @classmethod
  def sorted(cls, tasks, key = lambda task: task.line):
    return {i + 1: task for i, task in enumerate(sorted(tasks.values(), key = key))}

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
    self.tags = Tag.find_all(title)

  def __repr__(self):
    return self.line

  def __eq__(self, other):
    return other is not None and self.line.__eq__(other.line)

  def __ne__(self, other):
    return not self.__eq__(other)

  def __hash__(self):
    return self.line.__hash__()

  def remove_tags(self, tags):
    title = self.title
    for tag in tags & self.tags:
      title = title.replace(" " + tag.raw, "")
      title = title.replace(tag.raw + " ", "")
      title = title.replace(   tag.raw   , "")
    return Task(title, self.priority, self.create_date, self.complete_date)

  def add_tags(self, tags, prepend = False):
    title = self.title
    for tag in tags - self.tags:
      title = tag.raw + " " + title if prepend else title + " " + tag.raw
    return Task(title, self.priority, self.create_date, self.complete_date)

  def set_priority(self, priority):
    return Task(self.title, priority, self.create_date, self.complete_date)

  def set_create_date(self, create_date):
    return Task(self.title, self.priority, create_date, self.complete_date)


class BatchEditContext:
  def __init__(self, tasks, priority = None, tags = set()):
    self.tasks = tasks
    self.priority = priority
    self.tags = tags

  def get_editable_tasks(self):
    max_id = max(tasks.keys()) if len(tasks) > 0 else 0
    max_id_len = len(str(max_id))
    editable_tasks = {}
    for id, task in tasks.items():
      if task.tags >= self.tags and (not self.priority or task.priority == self.priority):
        id_tag = KeyValueTag("id", str(id).zfill(max_id_len))
        editable_task = task
        editable_task = editable_task.remove_tags(self.tags)
        editable_task = editable_task.set_priority(None if self.priority else task.priority)
        editable_task = editable_task.set_create_date(None)
        editable_task = editable_task.add_tags(set([id_tag]), prepend = True)
        editable_tasks[id] = editable_task
    return Task.sorted(editable_tasks)

  def merge_edited_tasks(self, edited_tasks):
    default_create_date = date.today() if date_on_add else None

    tasks = self.tasks.copy()
    for edited_task in edited_tasks.values():
      task = edited_task

      id = None
      for tag in task.tags:
        if isinstance(tag, KeyValueTag) and tag.key == "id":
          if id is None:
            tmpid = int(tag.value)
            if tmpid in tasks:
              id = tmpid
              task = task.remove_tags(set([tag]))
            else:
              log("ignoring invalid id: %s" % tag) #todo: test
          else:
            log("ignoring duplicate id: %s" % tag) #todo: test
      if id:
        existing_task = tasks[id]
      else:
        id = len(tasks) + 1
        existing_task = None

      task = task.set_create_date(existing_task.create_date if existing_task else default_create_date)
      task = task.set_priority((task.priority or self.priority) if not task.complete_date else None)
      task = task.add_tags(self.tags)

      if existing_task != task:
        if existing_task:
          log("- %d %s" % (id, existing_task))
        log("+ %d %s" % (id, task))
        tasks[id] = task

    return tasks


def edit(tasks):
  # we want the file to be named todo.txt for compatibility with syntax-highlighting editors
  with tempfile.TemporaryDirectory() as temp_dir_path:
    temp_todo_path = os.path.join(temp_dir_path, "todo.txt")
    Task.save_all(tasks, temp_todo_path)
    subprocess.check_call([editor_path, temp_todo_path])
    return Task.load_all(temp_todo_path)


def usage():
  # TODO: detect script name
  print("  batch.py [PRIORITY] [TAG...]")
  print("    Opens tasks matching PRIORITY and/or TAG(s) for batch editing in $EDITOR.")
  print("    After editing, changes will be merged back into todo.txt.")
  print("    PRIORITY and TAG(s) will be automatically applied.")
  print()


if __name__ == "__main__":
  action = sys.argv[1]
  args = sys.argv[2:]

  if action == "usage":
    usage()
    sys.exit(0)

  priority = None
  tags = set()

  if len(args) > 0 and len(args[0]) == 1:
    priority = args.pop(0)
    if priority not in string.ascii_uppercase:
      usage()
      sys.exit(1)

  while len(args) > 0:
    arg = args.pop()
    tag = Tag.parse(arg)
    if not tag:
      usage()
      sys.exit(1)
    tags.add(tag)

  tasks = Task.load_all(todo_file_path)

  ctx = BatchEditContext(tasks, priority, tags)
  editable_tasks = ctx.get_editable_tasks()
  edited_tasks = edit(editable_tasks)
  tasks2 = ctx.merge_edited_tasks(edited_tasks)
  Task.save_all(tasks2, todo_file_path)

