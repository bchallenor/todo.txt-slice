#!/usr/bin/env python3
from contextlib import contextmanager
from datetime import date
import imp
import logging
import os.path
import unittest

slice = imp.load_source("slice", "slice")


@contextmanager
def capture(log, level):
  records = []

  class MemoryHandler(logging.Handler):
    def emit(self, record):
      records.append(record)

  h = MemoryHandler()
  h.setLevel(level)
  log.addHandler(h)

  yield records

  log.removeHandler(h)


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

  def __init__(self, expect_clean_exit, todo0, edit0, edit1, todo1, date_on_add, preserve_line_numbers, disable_filter, slice_review_intervals):
    unittest.TestCase.__init__(self)

    self.expect_clean_exit = expect_clean_exit

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
    self.slice_review_intervals = slice_review_intervals

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

  def print_diff(self, id, task_a, task_b):
    self.assertNotEqual(task_a, task_b)

  def assert_success(self):
    if self.expect_clean_exit:
      self.assertTrue(self.__edit_dir.clean_exit, msg = "Expected edit directory to be used and cleaned up")
      self.assertTrue(self.__edit_file_path_written, msg = "Expected edit file to be written")
      changes = self.__todo0 != self.__todo1
      if changes:
        self.assertTrue(self.__todo_file_path_written, msg = "Expected todo file to be written")
      else:
        self.assertFalse(self.__todo_file_path_written, msg = "Expected todo file to be untouched as there were no changes")
    else:
      self.assertFalse(self.__edit_dir.clean_exit, msg = "Expected edit directory to be untouched")
      self.assertFalse(self.__edit_file_path_written, msg = "Expected edit file to be untouched")
      self.assertFalse(self.__todo_file_path_written, msg = "Expected todo file to be untouched")


class AbstractSliceTest:
  action_name = "slice"

  def run_test(
      self,
      slice_args = [],
      expect_clean_exit = True,
      expect_warnings = False,
      todo0 = None,
      edit0 = None,
      edit1 = None,
      todo1 = None,
      date_on_add = False,
      preserve_line_numbers = True,
      disable_filter = False,
      slice_review_intervals = ""
      ):

    args = ["dummy.py"]

    if self.action_name is not None:
      args.append(self.action_name)

      if self.slice_name is not None:
        args.append(self.slice_name)
        args.extend(slice_args)

    env = VirtualTodoEnv(
        expect_clean_exit = expect_clean_exit,
        todo0 = todo0,
        edit0 = edit0,
        edit1 = edit1 if edit1 is not None else edit0,
        todo1 = todo1 if todo1 is not None else todo0,
        date_on_add = date_on_add,
        preserve_line_numbers = preserve_line_numbers,
        disable_filter = disable_filter,
        slice_review_intervals = slice_review_intervals
        )

    with capture(logging.getLogger("slice"), logging.WARN) as warnings:

      slice.main(env, args)

      have_warnings = len(warnings) > 0
      if expect_warnings:
        self.assertTrue(have_warnings, "Expected warnings")
      else:
        self.assertFalse(have_warnings, msg = "Expected no warnings: %s" % warnings)

    env.assert_success()


  # the tests in this class should work with any slice as they start empty

  def test_no_tasks(self):
    self.run_test(
        todo0 = [],
        edit0 = []
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

  def test_duplicate_start_dates(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["x t:1999-12-31 t:1999-12-31"],
        todo1 = ["x t:1999-12-31"],
        expect_warnings = True
        )

  def test_multiple_start_dates(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["x t:1999-12-30 t:1999-12-31"],
        todo1 = ["x t:1999-12-30"],
        expect_warnings = True
        )

  # regression test
  def test_insert_task_with_explicit_no_level(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["(_) new"],
        todo1 = ["new"]
        )

  def test_unknown_id_tag_ignored(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["i:42 x"],
        todo1 = ["x"],
        expect_warnings = True
        )

  # regression test
  def test_invalid_id_tag_ignored(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["i:foo x"],
        todo1 = ["x"],
        expect_warnings = True
        )


class SliceAllTest(AbstractSliceTest, unittest.TestCase):
  slice_name = "all"

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

  def test_remove_task(self):
    self.run_test(
        todo0 = ["x"],
        edit0 = ["i:1 x"],
        edit1 = [],
        todo1 = [],
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

  def test_empty_line_unchanged_if_no_other_edits(self):
    self.run_test(
        todo0 = ["", "orig"],
        edit0 = ["i:2 orig"],
        edit1 = ["i:2 orig"],
        todo1 = ["", "orig"],
        preserve_line_numbers = False
        )

  def test_empty_line_not_preserved_when_other_edits(self):
    self.run_test(
        todo0 = ["", "orig"],
        edit0 = ["i:2 orig"],
        edit1 = ["i:2 changed"],
        todo1 = ["changed"],
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

  # regression test
  def test_url_is_not_considered_tag(self):
    self.run_test(
        todo0 = ["http://example.com @c"],
        edit0 = ["i:1 http://example.com @c"]
        )

  def test_duplicate_id_tag_ignored(self):
    self.run_test(
        todo0 = ["a"],
        edit0 = ["i:1 a"],
        edit1 = ["i:1 i:1 x"],
        todo1 = ["x"],
        expect_warnings = True
        )


class SliceMatchTest(SliceAllTest):
  slice_name = "match"

  def test_match_task_with_priority(self):
    self.run_test(
        slice_args = ["A"],
        todo0 = ["x", "(A) a"],
        edit0 = ["i:2 a"]
        )

  def test_match_task_with_no_level_priority(self):
    self.run_test(
        slice_args = ["_"],
        todo0 = ["x", "(A) a"],
        edit0 = ["i:1 x"]
        )

  def test_match_task_with_context(self):
    self.run_test(
        slice_args = ["@c"],
        todo0 = ["x", "a @c"],
        edit0 = ["i:2 a"]
        )

  def test_match_task_with_project(self):
    self.run_test(
        slice_args = ["+p"],
        todo0 = ["x", "a +p"],
        edit0 = ["i:2 a"]
        )

  def test_match_task_with_kv(self):
    self.run_test(
        slice_args = ["k:v"],
        todo0 = ["x", "a k:v"],
        edit0 = ["i:2 a"]
        )

  def test_match_task_hides_but_preserves_date(self):
    self.run_test(
        slice_args = ["A"],
        todo0 = ["(A) 1999-12-31 a"],
        edit0 = ["i:1 a"]
        )

  def test_forged_id_tag_ignored(self):
    self.run_test(
        slice_args = ["A"],
        todo0 = ["(B) b"],
        edit0 = [],
        edit1 = ["i:1 a"],
        todo1 = ["(B) b", "(A) a"],
        expect_warnings = True
        )

  def test_insert_task_with_no_level_priority(self):
    self.run_test(
        slice_args = ["_"],
        todo0 = [],
        edit0 = [],
        edit1 = ["y"],
        todo1 = ["y"]
        )

  def test_insert_task_with_duplicate_tag(self):
    self.run_test(
        slice_args = ["@c"],
        todo0 = [],
        edit0 = [],
        edit1 = ["y @c"],
        todo1 = ["y @c"]
        )

  def test_insert_task_with_multiple_tags(self):
    self.run_test(
        slice_args = ["A", "@c", "+p", "k:v"],
        todo0 = [],
        edit0 = [],
        edit1 = ["y"],
        todo1 = ["(A) y @c +p k:v"]
        )

  def test_edit_task_with_multiple_tags(self):
    self.run_test(
        slice_args = ["A", "@c", "+p", "k:v"],
        todo0 = ["x", "(A) a @c +p k:v", "(A) a +q"],
        edit0 = ["i:2 a"],
        edit1 = ["i:2 y"],
        todo1 = ["x", "(A) y @c +p k:v", "(A) a +q"]
        )


class SliceReviewTest(AbstractSliceTest, unittest.TestCase):
  slice_name = "review"

  def test_reviewable_by_age(self):
    self.run_test(
        slice_review_intervals = "A:1",
        todo0 = ["(A) 1999-12-31 a"],
        edit0 = ["(_) i:1 a"]
        )

  def test_not_reviewable_by_age(self):
    self.run_test(
        slice_review_intervals = "A:2",
        todo0 = ["(A) 1999-12-31 a"],
        edit0 = []
        )

  def test_reviewable_by_priority(self):
    self.run_test(
        slice_review_intervals = "A:0,B:1",
        todo0 = ["(A) 2000-01-01 a", "(B) 2000-01-01 b"],
        edit0 = ["(_) i:1 a"]
        )

  def test_reviewable_by_no_priority(self):
    self.run_test(
        slice_review_intervals = "_:0,B:1",
        todo0 = ["2000-01-01 a", "(B) 2000-01-01 b"],
        edit0 = ["(_) i:1 a"]
        )

  def test_reviewable_by_unconfigured_priority(self):
    self.run_test(
        slice_review_intervals = "A:1",
        todo0 = ["(A) 2000-01-01 a", "(B) 2000-01-01 b"],
        edit0 = ["(_) i:2 b"]
        )

  def test_reviewable_by_start_date(self):
    self.run_test(
        slice_review_intervals = "_:5",
        todo0 = ["1999-12-31 a t:2000-01-01", "1999-12-31 b t:2000-01-02"],
        edit0 = ["(_) i:1 a t:2000-01-01"]
        )

  def test_set_complete_date_does_not_reset_create_date(self):
    self.run_test(
        slice_review_intervals = "A:1",
        todo0 = ["(A) 1999-12-31 a"],
        edit0 = ["(_) i:1 a"],
        edit1 = ["x 2000-01-01 (_) i:1 a"],
        todo1 = ["x 2000-01-01 1999-12-31 a"],
        )

  def test_set_complete_date_clears_start_date(self):
    self.run_test(
        slice_review_intervals = "_:5",
        todo0 = ["1999-12-31 a t:2000-01-01"],
        edit0 = ["(_) i:1 a t:2000-01-01"],
        edit1 = ["x 2000-01-01 (_) i:1 a t:2000-01-01"],
        todo1 = ["x 2000-01-01 1999-12-31 a"],
        )

  def test_set_start_date_resets_create_date(self):
    self.run_test(
        slice_review_intervals = "A:1",
        todo0 = ["(A) 1999-12-31 a"],
        edit0 = ["(_) i:1 a"],
        edit1 = ["(_) i:1 a t:2001-01-02"],
        todo1 = ["(A) 2000-01-01 a t:2001-01-02"],
        )

  def test_set_start_date_does_not_clear_start_date(self):
    self.run_test(
        slice_review_intervals = "_:5",
        todo0 = ["1999-12-31 a t:2000-01-01"],
        edit0 = ["(_) i:1 a t:2000-01-01"],
        edit1 = ["(_) i:1 a t:2001-01-02"],
        todo1 = ["2000-01-01 a t:2001-01-02"],
        )

  def test_set_priority_resets_create_date(self):
    self.run_test(
        slice_review_intervals = "A:1",
        todo0 = ["(A) 1999-12-31 a"],
        edit0 = ["(_) i:1 a"],
        edit1 = ["(B) i:1 a"],
        todo1 = ["(B) 2000-01-01 a"],
        )

  def test_set_priority_clears_start_date(self):
    self.run_test(
        slice_review_intervals = "_:5",
        todo0 = ["1999-12-31 a t:2000-01-01"],
        edit0 = ["(_) i:1 a t:2000-01-01"],
        edit1 = ["(B) i:1 a t:2000-01-01"],
        todo1 = ["(B) 2000-01-01 a"],
        )

  def test_edits_preserved(self):
    self.run_test(
        slice_review_intervals = "A:1",
        todo0 = ["(A) 1999-12-31 a"],
        edit0 = ["(_) i:1 a"],
        edit1 = ["(_) i:1 b"],
        todo1 = ["(A) 1999-12-31 b"],
        )

  # regression test
  def test_insert_hidden_sets_create_date(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["a t:2000-01-02"],
        todo1 = ["2000-01-01 a t:2000-01-02"],
        )


class SliceFutureTest(AbstractSliceTest, unittest.TestCase):
  slice_name = "future"

  def test_future_start_date(self):
    self.run_test(
        todo0 = ["future t:2000-01-02"],
        edit0 = ["i:1 future t:2000-01-02"]
        )

  def test_past_or_present_start_dates_hidden(self):
    self.run_test(
        todo0 = ["past t:1999-12-31", "present t:2000-01-01"],
        edit0 = []
        )

  def test_normal_hidden(self):
    self.run_test(
        todo0 = ["normal"],
        edit0 = []
        )

  def test_completed_hidden(self):
    self.run_test(
        todo0 = ["x 2000-01-01 completed"],
        edit0 = []
        )

  # regression test
  def test_completed_future_start_date_hidden(self):
    self.run_test(
        todo0 = ["x 2000-01-01 completed t:2000-01-02"],
        edit0 = []
        )

  # regression test
  def test_completed_future_start_date_not_hidden(self):
    self.run_test(
        todo0 = ["x 2000-01-01 completed t:2000-01-02"],
        edit0 = ["x 2000-01-01 i:1 completed t:2000-01-02"],
        disable_filter = True
        )

  def test_sorted_by_start_date(self):
    self.run_test(
        todo0 = ["(A) a t:2000-01-04", "(C) c t:2000-01-03", "(B) b t:2000-01-02"],
        edit0 = ["(B) i:3 b t:2000-01-02", "(C) i:2 c t:2000-01-03", "(A) i:1 a t:2000-01-04"]
        )


if __name__ == "__main__":
  unittest.main()

