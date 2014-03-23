todo.txt-slice: Slices tasks for batch editing
============================================================

Slice is a plugin for [todo.txt](http://todotxt.com/). It "slices" a subset of your `todo.txt` tasks into your favourite `EDITOR` for batch editing. After you save and close your `EDITOR`, it merges the edited tasks back into your `todo.txt` file, printing a colorized diff to the console so you can easily see what has changed.

Several different "slices" are provided:

- _all_ opens all tasks
- _terms_ opens tasks matching the given search terms
- _tags_ opens tasks matching the given priority or tags; any new tasks created will automatically have these applied
- _future_ opens tasks with a start date (`t:<date>`) in the future (compatible with the [future-tasks](https://github.com/ginatrapani/todo.txt-cli/wiki/Todo.sh-Add-on-Directory#future-tasks) plugin)
- _review_ opens tasks that need reviewing, based on their age and priority

Slice works best if your `EDITOR` has a plugin for the `todo.txt` format. For example, in Vim you can use [todo.txt-vim](https://github.com/freitass/todo.txt-vim).


Example
-------

Imagine we want to work on the `+Report` project. For this we'll want the _tags_ slice:

```
todo.sh slice tags +Report
```

Slice opens all the tasks tagged with `+Report` in our `EDITOR`:

```
(B) i:2 Write introduction chapter @Computer
```

Note that Slice has hidden the project and the date, but they will be preserved if we make changes. To do this, Slice has injected the line number of the underlying task as a tag (`i:2`).

Imagine we want to complete this task and add another one. Because the tasks are in `todo.txt` format, we can do this just as if we were editing our todo file directly:

```
x 2014-01-01 (B) i:2 Write introduction chapter @Computer
(B) Collect results @Lab
```

If we close the editor, Slice will write these changes back to our todo file:

```
...
x 2014-01-10 Write introduction chapter @Computer +Report
...
(B) Collect results @Lab +Report
```

Note that `+Report` has been automatically applied to the new task. If you like to add creation dates to your tasks, Slice can do this too. Just start `todo.sh` with `-t` as usual.


Installation
------------

Slice works on Linux, Mac OS X and Windows (Cygwin). It requires Python 3.

To install Slice, copy the `slice` file to your `todo.txt` add-on directory.

For more information see [Installing Add-ons](https://github.com/ginatrapani/todo.txt-cli/wiki/Creating-and-Installing-Add-ons#installing-add-ons) on the `todo.txt` wiki.


Tests
-----

Slice has a comprehensive suite of tests, verifying the state of the `todo.txt` file before and after a given edit.

To run them:

```
$ ./test-slice.py
Ran 219 tests in 0.127s

OK
```


License
-------

    Copyright (C) 2013 Ben Challenor <ben@challenor.org>

    Permission is hereby granted, free of charge, to any person obtaining a copy of
    this software and associated documentation files (the "Software"), to deal in
    the Software without restriction, including without limitation the rights to
    use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
    the Software, and to permit persons to whom the Software is furnished to do so,
    subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
    FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
    COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
    IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
    CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

