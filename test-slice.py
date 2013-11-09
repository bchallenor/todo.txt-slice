#!/usr/bin/env python3
from datetime import date
import imp
import os.path
import unittest

slice = imp.load_source("slice", "slice")


class VirtualTempDir:
  def __init__(self, path):
    self.__path = path
    self.clean_exit = False

  def __enter__(self):
    return self.__path

  def __exit__(self, exc_type, exc_value, traceback):
    self.clean_exit = exc_type is None


class VirtualTodoEnv(unittest.TestCase):
  todo_file_name = "todo.txt"
  __edit_dir_path = "EDIT"
  __edit_file_path = os.path.join(__edit_dir_path, todo_file_name)
  todo_dir_path = "TODO"
  todo_file_path = os.path.join(todo_dir_path, todo_file_name)
  today = date(2000, 1, 1)

  def __init__(self, todo0, edit0, edit1, todo1, date_on_add, preserve_line_numbers, disable_filter):
    unittest.TestCase.__init__(self)

    self.__todo0 = todo0
    self.__edit0 = edit0
    self.__edit1 = edit1
    self.__todo1 = todo1

    self.__edit_dir = VirtualTempDir(self.__edit_dir_path)
    self.__edit_file_path_written = False
    self.__todo_file_path_written = False

    self.date_on_add = date_on_add
    self.default_create_date = self.today if date_on_add else None
    self.preserve_line_numbers = preserve_line_numbers
    self.disable_filter = disable_filter

  def read_lines(self, path):
    if path == self.todo_file_path:
      return self.__todo0
    elif path == self.__edit_file_path:
      return self.__edit1
    else:
      self.fail("attempt to read unknown path: %s" % path)

  def write_lines(self, path, lines):
    if path == self.todo_file_path:
      self.assertEqual(self.__todo1, lines, msg = "Todo file content does not match expected content")
      self.__todo_file_path_written = True
    elif path == self.__edit_file_path:
      self.assertEqual(self.__edit0, lines, msg = "Slice file content does not match expected content")
      self.__edit_file_path_written = True
    else:
      self.fail("attempt to write unknown path: %s" % path)

  def create_temp_dir(self):
    return self.__edit_dir

  def launch_editor(self, path):
    self.assertEqual(self.__edit_file_path, path)

  def assert_success(self):
    self.assertTrue(self.__edit_dir.clean_exit, msg = "Expected edit directory to be used and cleaned up")
    self.assertTrue(self.__edit_file_path_written, msg = "Expected edit file to be written")
    self.assertTrue(self.__todo_file_path_written, msg = "Expected todo file to be written")


class SliceTest(unittest.TestCase):
  action_name = "slice"

  def run_test(
      self,
      filter_args = [],
      expect_early_exit = False,
      todo0 = None,
      edit0 = None,
      edit1 = None,
      todo1 = None,
      date_on_add = False,
      preserve_line_numbers = True,
      disable_filter = False
      ):

    args = ["dummy.py"]

    if self.action_name is not None:
      args.append(self.action_name)

      if self.filter_name is not None:
        args.append(self.filter_name)
        args.extend(filter_args)

    env = VirtualTodoEnv(
        todo0 = todo0,
        edit0 = edit0,
        edit1 = edit1 if edit1 is not None else edit0,
        todo1 = todo1 if todo1 is not None else todo0,
        date_on_add = date_on_add,
        preserve_line_numbers = preserve_line_numbers,
        disable_filter = disable_filter
        )

    slice.main(env, args)

    if not expect_early_exit:
      env.assert_success()


class SliceMatchTest(SliceTest):
  filter_name = "match"

  def test_single_task(self):
    self.run_test(
        todo0 = ["task"],
        edit0 = ["i:1 task"]
        )

  def test_completed_tasks_are_hidden(self):
    self.run_test(
        todo0 = ["x 2000-01-01 done"],
        edit0 = []
        )

  def test_empty_line_is_preserved(self):
    self.run_test(
        todo0 = ["", "orig"],
        edit0 = ["i:2 orig"],
        edit1 = ["i:2 orig", "new"],
        todo1 = ["", "orig", "new"],
        preserve_line_numbers = True
        )


if __name__ == "__main__":
  unittest.main()

