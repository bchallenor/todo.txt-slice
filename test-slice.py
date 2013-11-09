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


class SliceBasicTest(SliceTest):
  filter_name = "match"

  def test_no_tasks(self):
    self.run_test(
        todo0 = [],
        edit0 = []
        )

  def test_single_task(self):
    self.run_test(
        todo0 = ["task"],
        edit0 = ["i:1 task"]
        )

  def test_tasks_sorted(self):
    self.run_test(
        todo0 = ["(C) c", "(B) b", "(A) a"],
        edit0 = ["(A) i:3 a", "(B) i:2 b", "(C) i:1 c"]
        )

  def test_completed_tasks_hidden(self):
    self.run_test(
        todo0 = ["x 2000-01-01 done"],
        edit0 = []
        )

  def test_completed_tasks_not_hidden(self):
    self.run_test(
        todo0 = ["x 2000-01-01 done"],
        edit0 = ["x 2000-01-01 i:1 done"],
        disable_filter = True
        )

  def test_future_tasks_hidden(self):
    self.run_test(
        todo0 = ["past t:1999-12-31", "present t:2000-01-01", "future t:2000-01-02"],
        edit0 = ["i:1 past t:1999-12-31", "i:2 present t:2000-01-01"]
        )

  def test_future_tasks_not_hidden(self):
    self.run_test(
        todo0 = ["past t:1999-12-31", "present t:2000-01-01", "future t:2000-01-02"],
        edit0 = ["i:1 past t:1999-12-31", "i:2 present t:2000-01-01", "i:3 future t:2000-01-02"],
        disable_filter = True
        )

  def test_insert_task(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["x"],
        todo1 = ["x"],
        )

  def test_insert_task_with_date(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["x"],
        todo1 = ["2000-01-01 x"],
        date_on_add = True
        )

  def test_edit_task(self):
    self.run_test(
        todo0 = ["a", "b"],
        edit0 = ["i:1 a", "i:2 b"],
        edit1 = ["i:1 x", "i:2 b"],
        todo1 = ["x", "b"],
        )

  def test_empty_line_preserved(self):
    self.run_test(
        todo0 = ["", "orig"],
        edit0 = ["i:2 orig"],
        edit1 = ["i:2 orig"],
        todo1 = ["", "orig"]
        )

  def test_empty_line_not_preserved(self):
    self.run_test(
        todo0 = ["", "orig"],
        edit0 = ["i:2 orig"],
        edit1 = ["i:2 orig"],
        todo1 = ["orig"],
        preserve_line_numbers = False
        )

  # regression test
  def test_insert_task_empty_line_preserved(self):
    self.run_test(
        todo0 = ["", "orig"],
        edit0 = ["i:2 orig"],
        edit1 = ["i:2 orig", "new"],
        todo1 = ["", "orig", "new"]
        )

  # regression test
  def test_insert_task_empty_line_not_preserved(self):
    self.run_test(
        todo0 = ["", "orig"],
        edit0 = ["i:2 orig"],
        edit1 = ["i:2 orig", "new"],
        todo1 = ["orig", "new"],
        preserve_line_numbers = False
        )

  def test_canonicalizes_trailing_tag_order(self):
    self.run_test(
        todo0 = ["x +p1 @c1 k2:v @c2 +p2 k1:v"],
        edit0 = ["i:1 x +p1 @c1 k2:v @c2 +p2 k1:v"],
        todo1 = ["x @c1 @c2 +p1 +p2 k1:v k2:v"]
        )


class SliceMatchTest(SliceTest):
  filter_name = "match"

  def test_match_task_with_priority(self):
    self.run_test(
        filter_args = ["A"],
        todo0 = ["x", "(A) a"],
        edit0 = ["i:2 a"]
        )

  def test_match_task_with_context(self):
    self.run_test(
        filter_args = ["@c"],
        todo0 = ["x", "a @c"],
        edit0 = ["i:2 a"]
        )

  def test_match_task_with_project(self):
    self.run_test(
        filter_args = ["+p"],
        todo0 = ["x", "a +p"],
        edit0 = ["i:2 a"]
        )

  def test_match_task_with_kv(self):
    self.run_test(
        filter_args = ["k:v"],
        todo0 = ["x", "a k:v"],
        edit0 = ["i:2 a"]
        )

  def test_insert_task_with_multiple(self):
    self.run_test(
        filter_args = ["A", "@c", "+p", "k:v"],
        todo0 = [],
        edit0 = [],
        edit1 = ["y"],
        todo1 = ["(A) y @c +p k:v"]
        )

  def test_edit_task_with_multiple(self):
    self.run_test(
        filter_args = ["A", "@c", "+p", "k:v"],
        todo0 = ["x", "(A) a @c +p k:v", "(A) a +q"],
        edit0 = ["i:2 a"],
        edit1 = ["i:2 y"],
        todo1 = ["x", "(A) y @c +p k:v", "(A) a +q"]
        )


if __name__ == "__main__":
  unittest.main()

