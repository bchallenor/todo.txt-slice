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
default_create_date = date.today() if date_on_add else None
preserve_line_numbers = os.environ["TODOTXT_PRESERVE_LINE_NUMBERS"] == "1"


class Tag:
  __tag_re = re.compile(r"""
    (
      (?P<prefix> [@+] )(?P<name> \S+ )
    |
      (?P<key> \S+? ) : (?P<value> \S+ )
    )
  """, re.VERBOSE)

  @staticmethod
  def __handle_match(m):
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
    m = cls.__tag_re.match(raw)
    if m and m.group(0) == raw: # check the whole string was matched
      return cls.__handle_match(m)
    else:
      return None

  @classmethod
  def find_all(cls, raw):
    return {cls.__handle_match(m) for m in cls.__tag_re.finditer(raw)}

  def sort_key(self):
    raise NotImplementedError

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

  def sort_key(self):
    return (0, self.name, None)


class ProjectTag(Tag):
  def __init__(self, name):
    self.name = name
    Tag.__init__(self, "+" + name)

  def sort_key(self):
    return (1, self.name, None)


class KeyValueTag(Tag):
  def __init__(self, key, value):
    self.key = key
    self.value = value
    Tag.__init__(self, key + ":" + value)

  def sort_key(self):
    return (2, self.key, self.value)


class Task:
  __task_re = re.compile(r"""
    ^
    ( x \s+ (?P<complete> [0-9]{4}-[0-9]{2}-[0-9]{2} ) \s+ )?
    ( \( (?P<priority> [A-Z] ) \) \s+ )?
    ( (?P<create> [0-9]{4}-[0-9]{2}-[0-9]{2} ) \s+ )?
    (?P<title> .*? )
    $
  """, re.VERBOSE)

  @staticmethod
  def __parse_date(date_str):
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
    m = cls.__task_re.match(line)
    assert m is not None, "__task_re should match all lines: %s" % line
    title = m.group("title")
    priority = m.group("priority")
    create_date = cls.__parse_date(m.group("create"))
    complete_date = cls.__parse_date(m.group("complete"))
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
    for tag in sorted(tags - self.tags, key = lambda tag: tag.sort_key()):
      title = tag.raw + " " + title if prepend else title + " " + tag.raw
    return Task(title, self.priority, self.create_date, self.complete_date)

  def set_priority(self, priority):
    return Task(self.title, priority, self.create_date, self.complete_date)

  def set_create_date(self, create_date):
    return Task(self.title, self.priority, create_date, self.complete_date)


class TaskFilter:
  def matches(task):
    raise NotImplementedError

  def apply(task):
    raise NotImplementedError

  def unapply(filtered_task):
    raise NotImplementedError


class EditTaskFilter(TaskFilter):
  def __init__(self, priority = None, tags = set()):
    self.priority = priority
    self.tags = tags

  def matches(self, task):
    return (not self.priority or task.priority == self.priority) and task.tags >= self.tags

  def apply(self, task):
    filtered_task = task
    filtered_task = filtered_task.remove_tags(self.tags)
    filtered_task = filtered_task.set_priority(None if self.priority else task.priority)
    filtered_task = filtered_task.set_create_date(None)
    return filtered_task

  def unapply(self, filtered_task, original_task):
    task = filtered_task
    task = task.set_create_date(original_task.create_date if original_task else default_create_date)
    task = task.set_priority((task.priority or self.priority) if not task.complete_date else None)
    task = task.add_tags(self.tags)
    return task


class BatchEditor:
  def __init__(self, tasks, task_filter):
    self.tasks = tasks
    self.task_filter = task_filter
    self.editable_tasks = self.__get_editable_tasks(tasks, task_filter)
    self.sorted_editable_tasks = Task.sorted(self.editable_tasks)

  @staticmethod
  def __get_editable_tasks(tasks, task_filter):
    max_id = max(tasks.keys()) if len(tasks) > 0 else 0
    max_id_len = len(str(max_id))
    editable_tasks = {}
    for id, task in tasks.items():
      if task_filter.matches(task):
        id_tag = KeyValueTag("id", str(id).zfill(max_id_len))
        editable_task = task_filter.apply(task)
        editable_task = editable_task.add_tags(set([id_tag]), prepend = True)
        editable_tasks[id] = editable_task
    return editable_tasks

  def __recover_task_ids(self, edited_tasks):
    recovered_edited_tasks = {}
    next_id = len(self.tasks) + 1
    for task in edited_tasks.values():
      id = None
      for tag in task.tags:
        if isinstance(tag, KeyValueTag) and tag.key == "id":
          if id is None:
            tmpid = int(tag.value)
            task = task.remove_tags(set([tag]))
            if tmpid in self.editable_tasks: # safety check
              id = tmpid
            else:
              log("ignoring invalid id: %s" % tag) #todo: test
          else:
            log("ignoring duplicate id: %s" % tag) #todo: test
      if id is None:
        id = next_id
        next_id += 1
      recovered_edited_tasks[id] = task
    return recovered_edited_tasks

  def __merge_edited_tasks(self, edited_tasks):
    recovered_edited_tasks = self.__recover_task_ids(edited_tasks)
    merged_tasks = self.tasks.copy()

    for id in self.editable_tasks.keys() - recovered_edited_tasks.keys():
      existing_task = merged_tasks[id]
      log("- %d %s" % (id, existing_task))
      del merged_tasks[id]

    for id, edited_task in recovered_edited_tasks.items():
      existing_task = merged_tasks[id] if id in merged_tasks else None

      task = self.task_filter.unapply(edited_task, existing_task)

      if existing_task != task:
        if existing_task:
          log("- %d %s" % (id, existing_task))
        log("+ %d %s" % (id, task))
        merged_tasks[id] = task

    return merged_tasks

  @staticmethod
  def __edit(tasks):
    # we want the file to be named todo.txt for compatibility with syntax-highlighting editors
    with tempfile.TemporaryDirectory() as temp_dir_path:
      temp_todo_path = os.path.join(temp_dir_path, "todo.txt")
      Task.save_all(tasks, temp_todo_path)
      subprocess.check_call([editor_path, temp_todo_path])
      return Task.load_all(temp_todo_path)

  def edit_and_merge(self):
    edited_tasks = self.__edit(self.sorted_editable_tasks)
    merged_tasks = self.__merge_edited_tasks(edited_tasks)
    return merged_tasks


def usage():
  # TODO: detect script name
  print("  batch.py [PRIORITY] [TAG...]")
  print("    Opens tasks matching PRIORITY and/or TAG(s) for batch editing in $EDITOR.")
  print("    After editing, changes will be merged back into todo.txt.")
  print("    PRIORITY and TAG(s) will be automatically applied.")
  print()


def main(action, args):
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

  task_filter = EditTaskFilter(priority, tags)
  editor = BatchEditor(tasks, task_filter)
  merged_tasks = editor.edit_and_merge()
  Task.save_all(merged_tasks, todo_file_path)


if __name__ == "__main__":
  action = sys.argv[1]
  args = sys.argv[2:]
  main(action, args)

