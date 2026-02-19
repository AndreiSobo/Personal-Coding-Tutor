'use client'

import { useEffect, useState, useCallback } from 'react'

declare global {
  interface Window {
    loadPyodide: any
  }
}

export interface TestResult {
  index: number
  passed: boolean
  expected?: string
  actual?: string
  error?: string
}

export interface TestSummary {
  passed: number
  failed: number
  total: number
  results: TestResult[]
  allPassed: boolean
}

/**
 * Python preamble injected before user code.
 *
 * Sourced from the "prompt" column in newfacade/LeetCodeDataset.
 * There are only 4 variants in the dataset — this is the most comprehensive one,
 * covering all imports, data structures (TreeNode, ListNode), and helper functions
 * (tree_node, list_node, is_same_tree, is_same_list) needed across all 2,641 problems.
 */
const PYTHON_PREAMBLE = `
import random
import functools
import collections
import string
import math
import datetime

from typing import *
from functools import *
from collections import *
from itertools import *
from heapq import *
from bisect import *
from string import *
from operator import *
from math import *

inf = float('inf')

# Handle common non-Python literals that appear in test data
null = None
true = True
false = False

class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
    def __repr__(self):
        vals = []
        node = self
        while node and len(vals) < 20:
            vals.append(str(node.val))
            node = node.next
        return "[" + ", ".join(vals) + "]"

def list_node(values: list):
    if not values:
        return None
    head = ListNode(values[0])
    p = head
    for val in values[1:]:
        node = ListNode(val)
        p.next = node
        p = node
    return head

def is_same_list(p1, p2):
    if p1 is None and p2 is None:
        return True
    if not p1 or not p2:
        return False
    return p1.val == p2.val and is_same_list(p1.next, p2.next)

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
    def __repr__(self):
        return f"TreeNode({self.val})"

def tree_node(values: list):
    if not values:
        return None
    root = TreeNode(values[0])
    i = 1
    queue = collections.deque()
    queue.append(root)
    while queue:
        node = queue.popleft()
        if i < len(values) and values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root

def is_same_tree(p, q):
    if not p and not q:
        return True
    elif not p or not q:
        return False
    elif p.val != q.val:
        return False
    else:
        return is_same_tree(p.left, q.left) and is_same_tree(p.right, q.right)
`.trim()

/**
 * Maximum number of test cases to run per execution.
 * Keeps Pyodide responsive — some problems have 80+ tests.
 */
const MAX_TEST_CASES = 10

export default function usePyodide() {
  const [pyodide, setPyodide] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [output, setOutput] = useState<string[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [testSummary, setTestSummary] = useState<TestSummary | null>(null)

  // Initialize Pyodide on mount
  useEffect(() => {
    const initPyodide = async () => {
      try {
        while (typeof window.loadPyodide === 'undefined') {
          await new Promise((resolve) => setTimeout(resolve, 100))
        }

        const py = await window.loadPyodide({
          indexURL: "https://cdn.jsdelivr.net/pyodide/v0.25.0/full/"
        })

        setPyodide(py)
        setIsLoading(false)
        console.log("Pyodide ready")
      } catch (err) {
        console.error("Failed to load Pyodide:", err)
        setIsLoading(false)
      }
    }

    initPyodide()
  }, [])

  /**
   * Run user code freely (no test validation).
   * Used for experimentation / print debugging.
   */
  const runPython = useCallback(async (code: string) => {
    if (!pyodide) return
    setIsRunning(true)
    setOutput([])
    setTestSummary(null)

    try {
      pyodide.setStdout({
        batched: (msg: string) => {
          setOutput((prev) => [...prev, msg])
        }
      })

      const fullCode = `${PYTHON_PREAMBLE}\n\n${code}`
      await pyodide.runPythonAsync(fullCode)
    } catch (error: any) {
      setOutput((prev) => [...prev, `Error: ${error.message}`])
    } finally {
      setIsRunning(false)
    }
  }, [pyodide])

  /**
   * Run user code against structured input/output test cases.
   *
   * The input_output format from the dataset uses Python expression strings:
   *   input:  "nums = [3,3], target = 6"
   *   output: "[0, 1]"
   *
   * The harness evaluates these as Python expressions:
   *   eval("Solution().twoSum(nums = [3,3], target = 6)")
   *
   * The preamble provides tree_node(), list_node() and other helpers that are
   * available during eval, so test inputs that use these (e.g. for Tree problems)
   * will work correctly.
   */
  const runTests = useCallback(async (
    userCode: string,
    entryPoint: string,
    inputOutput: { input: string; output: string }[]
  ): Promise<TestSummary | null> => {
    if (!pyodide) return null
    setIsRunning(true)
    setOutput([])
    setTestSummary(null)

    const testSlice = inputOutput.slice(0, MAX_TEST_CASES)

    // Pass test data via Pyodide globals to avoid string escaping issues.
    // Test inputs contain quoted strings (e.g. firstWord = "ij") that break
    // when embedded inside triple-quoted Python strings.
    pyodide.globals.set('__pact_test_json', JSON.stringify(testSlice))
    pyodide.globals.set('__pact_entry_point', entryPoint)

    // Build the test harness
    const harness = `
${PYTHON_PREAMBLE}

${userCode}

import json as __json

__test_cases = __json.loads(__pact_test_json)
__entry_point = __pact_entry_point
__results = []

for __i, __tc in enumerate(__test_cases):
    try:
        __actual = eval(f"{__entry_point}({__tc['input']})")
        __expected = eval(__tc["output"])
        __passed = __actual == __expected
        __results.append(__json.dumps({
            "index": __i,
            "passed": __passed,
            "expected": __tc["output"],
            "actual": repr(__actual)
        }))
    except Exception as __e:
        __results.append(__json.dumps({
            "index": __i,
            "passed": False,
            "error": str(__e)
        }))

print("__PACT_TEST_RESULTS__")
for __r in __results:
    print(__r)
print("__PACT_TEST_RESULTS_END__")
`

    const capturedOutput: string[] = []

    try {
      pyodide.setStdout({
        batched: (msg: string) => {
          capturedOutput.push(msg)
        }
      })

      await pyodide.runPythonAsync(harness)

      // Parse structured results from output
      const resultsStart = capturedOutput.indexOf('__PACT_TEST_RESULTS__')
      const resultsEnd = capturedOutput.indexOf('__PACT_TEST_RESULTS_END__')

      if (resultsStart === -1 || resultsEnd === -1) {
        setOutput(capturedOutput)
        return null
      }

      const resultLines = capturedOutput.slice(resultsStart + 1, resultsEnd)
      const results: TestResult[] = resultLines.map((line) => {
        try {
          return JSON.parse(line)
        } catch {
          return { index: -1, passed: false, error: `Failed to parse: ${line}` }
        }
      })

      const passed = results.filter((r) => r.passed).length
      const summary: TestSummary = {
        passed,
        failed: results.length - passed,
        total: inputOutput.length,
        results,
        allPassed: passed === results.length && results.length > 0,
      }

      // Format output for the console
      const outputLines: string[] = []

      if (summary.allPassed) {
        outputLines.push(`✓ All ${summary.passed}/${Math.min(MAX_TEST_CASES, summary.total)} tests passed!`)
        if (summary.total > MAX_TEST_CASES) {
          outputLines.push(`  (${MAX_TEST_CASES} of ${summary.total} total tests run)`)
        }
      } else {
        outputLines.push(`✗ ${summary.passed}/${results.length} tests passed`)
        outputLines.push('')

        // Show details of failing tests (max 3)
        const failures = results.filter((r) => !r.passed).slice(0, 3)
        for (const f of failures) {
          if (f.error) {
            outputLines.push(`  Test ${f.index + 1}: Error — ${f.error}`)
          } else {
            outputLines.push(`  Test ${f.index + 1}: FAILED`)
            outputLines.push(`    Expected: ${f.expected}`)
            outputLines.push(`    Got:      ${f.actual}`)
          }
          outputLines.push('')
        }

        const remainingFailures = results.filter((r) => !r.passed).length - failures.length
        if (remainingFailures > 0) {
          outputLines.push(`  ... and ${remainingFailures} more failing test(s)`)
        }
      }

      setOutput(outputLines)
      setTestSummary(summary)
      return summary
    } catch (error: any) {
      setOutput([`Error: ${error.message}`])
      setTestSummary(null)
      return null
    } finally {
      setIsRunning(false)
    }
  }, [pyodide])

  return { runPython, runTests, output, isLoading, isRunning, testSummary }
}