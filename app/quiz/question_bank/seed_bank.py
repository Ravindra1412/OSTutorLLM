"""
app/quiz/question_bank/seed_bank.py

Section 5 (Static Question Bank) / Section 6 (organized by topic).
A curated, hand-written starter bank spanning every topic Section 6
requires and demonstrating every auto-gradable question type from
Section 3. This is intentionally a STARTER set (content authoring is
an ongoing, separate effort from the engine architecture that serves
it) — the Question Generator (app/quiz/services/question_generator.py)
is built to draw from this bank OR fall back to LLM generation
(Section 5) for any topic/difficulty combination not yet covered here,
so coverage grows without any code change, only data additions to this
file (or, in a later phase, a faculty-facing content upload feature —
Part 3.2's "Upload Notes" placeholder already anticipates this).

Shape of each entry (matches QuizQuestion's column shapes exactly, so
question_generator.py can insert these directly):
{
  "topic": str,              # must match a seeded Topic.name (database/seed/seed_data.py, Part 3.4)
  "question_text": str,
  "question_type": str,      # from app.quiz.question_types
  "options": list|dict|None, # raw Python, JSON-encoded by the generator at insert time
  "correct_answer": Any,     # raw Python, JSON-encoded by the generator at insert time
  "explanation": str,
  "difficulty_level": int,   # 1-5
  "points": float,
}
"""

STATIC_QUESTIONS = [
    # --- Linux Commands ---
    {
        "topic": "Navigation", "question_type": "mcq", "difficulty_level": 1, "points": 1.0,
        "question_text": "Which command prints the current working directory?",
        "options": ["pwd", "cd", "ls", "whoami"], "correct_answer": "pwd",
        "explanation": "`pwd` (print working directory) outputs the absolute path of where you currently are.",
    },
    {
        "topic": "Navigation", "question_type": "true_false", "difficulty_level": 1, "points": 1.0,
        "question_text": "`cd ..` moves you into a subdirectory of the current directory.",
        "options": None, "correct_answer": "false",
        "explanation": "`cd ..` moves UP one level, to the parent directory — not into a subdirectory.",
    },
    {
        "topic": "Navigation", "question_type": "command_prediction", "difficulty_level": 2, "points": 1.5,
        "question_text": "What command lists all files, including hidden ones, in long format?",
        "options": None, "correct_answer": "ls -la",
        "explanation": "`-l` gives long format (permissions, owner, size, date); `-a` includes dotfiles/hidden entries.",
    },

    # --- File Permissions ---
    {
        "topic": "File Permissions", "question_type": "mcq", "difficulty_level": 2, "points": 1.0,
        "question_text": "What does the octal permission `755` grant to the file's group and others?",
        "options": ["Read, write, execute", "Read, execute", "Write only", "No access"],
        "correct_answer": "Read, execute",
        "explanation": "7=rwx (owner), 5=r-x (group), 5=r-x (others) — group/others get read+execute, not write.",
    },
    {
        "topic": "File Permissions", "question_type": "fill_blank", "difficulty_level": 2, "points": 1.5,
        "question_text": "Complete the command to make `deploy.sh` executable: chmod ___ deploy.sh",
        "options": None, "correct_answer": ["+x", "u+x", "755", "775"],
        "explanation": "Any of `+x`, `u+x`, or an octal mode with the execute bit set (e.g. 755) works.",
    },
    {
        "topic": "File Permissions", "question_type": "multi_select", "difficulty_level": 3, "points": 2.0,
        "question_text": "Which of the following are valid symbolic permission classes in `chmod`? (select all that apply)",
        "options": ["u (user/owner)", "g (group)", "o (others)", "x (execute)", "a (all)"],
        "correct_answer": ["u (user/owner)", "g (group)", "o (others)", "a (all)"],
        "explanation": "u/g/o/a are permission CLASSES; x is a permission TYPE (execute), not a class.",
    },
    {
        "topic": "File Permissions", "question_type": "error_identification", "difficulty_level": 3, "points": 2.0,
        "question_text": "What's wrong with this script?\n```bash\n#!/bin/bash\nfor f in *.txt\n  do cat $f\ndone\n```",
        "options": None, "correct_answer": "The variable $f is unquoted in `cat $f`, which breaks on filenames containing spaces.",
        "explanation": "Always quote variable expansions holding filenames: `cat \"$f\"`.",
    },

    # --- Piping & Redirection / Shell Programming ---
    {
        "topic": "Piping & Redirection", "question_type": "output_prediction", "difficulty_level": 2, "points": 1.5,
        "question_text": "What does `echo \"hello\" | wc -c` print?",
        "options": None, "correct_answer": "6",
        "explanation": "\"hello\" is 5 characters plus the trailing newline `echo` adds = 6 bytes counted by `wc -c`.",
    },
    {
        "topic": "Piping & Redirection", "question_type": "mcq", "difficulty_level": 1, "points": 1.0,
        "question_text": "Which operator appends output to a file instead of overwriting it?",
        "options": [">", ">>", "|", "<"], "correct_answer": ">>",
        "explanation": "`>` overwrites/truncates; `>>` appends to the end of the existing file.",
    },

    # --- Loops / Shell Programming ---
    {
        "topic": "Loops", "question_type": "output_prediction", "difficulty_level": 2, "points": 1.5,
        "question_text": "What does this print?\n```bash\nfor i in 1 2 3; do echo $i; done\n```",
        "options": None, "correct_answer": "1\n2\n3",
        "explanation": "Each iteration echoes one value, each on its own line.",
    },
    {
        "topic": "Loops", "question_type": "shell_programming", "difficulty_level": 3, "points": 2.5,
        "question_text": "Write a Bash for-loop that prints the numbers 1 through 5.",
        "options": None, "correct_answer": "for i in 1 2 3 4 5; do echo $i; done",
        "explanation": "A `for ... in` loop over an explicit list, or a C-style `for ((i=1;i<=5;i++))`, both work.",
    },
    {
        "topic": "Loops", "question_type": "true_false", "difficulty_level": 1, "points": 1.0,
        "question_text": "A `while` loop in Bash continues as long as its condition evaluates to true (exit status 0).",
        "options": None, "correct_answer": "true",
        "explanation": "Bash conditions are evaluated by exit status — 0 means success/true.",
    },

    # --- Conditionals ---
    {
        "topic": "Conditionals", "question_type": "error_identification", "difficulty_level": 3, "points": 2.0,
        "question_text": "Find the bug:\n```bash\nif [ $count = 5 ]\n  echo \"Count reached\"\nfi\n```",
        "options": None, "correct_answer": "Missing `then` after the `if` condition.",
        "explanation": "Bash's `if` syntax requires `then` on the same or next line: `if [ $count = 5 ]; then`.",
    },
    {
        "topic": "Conditionals", "question_type": "mcq", "difficulty_level": 2, "points": 1.0,
        "question_text": "Which test checks if a file exists and is a regular file?",
        "options": ["-d", "-f", "-x", "-z"], "correct_answer": "-f",
        "explanation": "-d tests for a directory, -f for a regular file, -x for executable, -z for an empty string.",
    },

    # --- Process Management ---
    {
        "topic": "Process Management", "question_type": "mcq", "difficulty_level": 2, "points": 1.0,
        "question_text": "Which command sends SIGKILL to a process with PID 1234?",
        "options": ["kill 1234", "kill -9 1234", "kill -1 1234", "killall 1234"],
        "correct_answer": "kill -9 1234",
        "explanation": "Signal 9 is SIGKILL — an immediate, unblockable termination. Plain `kill` sends SIGTERM (15).",
    },
    {
        "topic": "Process Management", "question_type": "match_the_following", "difficulty_level": 3, "points": 2.0,
        "question_text": "Match each process state to its description.",
        "options": {
            "left": ["Running", "Waiting", "Zombie", "Stopped"],
            "right": [
                "Terminated but not yet reaped by its parent",
                "Currently executing on the CPU",
                "Suspended, e.g. via SIGSTOP",
                "Blocked waiting on an event or resource",
            ],
        },
        "correct_answer": {"0": "1", "1": "3", "2": "0", "3": "2"},
        "explanation": "Running->executing, Waiting->blocked on event, Zombie->terminated-not-reaped, Stopped->suspended.",
    },

    # --- Memory Management ---
    {
        "topic": "Memory Management", "question_type": "mcq", "difficulty_level": 3, "points": 1.5,
        "question_text": "In paging, what is a 'page fault'?",
        "options": [
            "A hardware crash", "An attempt to access a page not currently in physical memory",
            "A permission error", "A disk read error",
        ],
        "correct_answer": "An attempt to access a page not currently in physical memory",
        "explanation": "A page fault triggers the OS to load the required page from disk (or a backing store) into RAM.",
    },
    {
        "topic": "Memory Management", "question_type": "scenario", "difficulty_level": 4, "points": 3.0,
        "question_text": "A process keeps causing page faults right after every context switch back to it. What memory-management phenomenon does this suggest, and why?",
        "options": None,
        "correct_answer": "Thrashing — the process's working set doesn't fit in its allocated frames, so pages are constantly evicted and immediately needed again.",
        "explanation": "Thrashing occurs when a process spends more time paging than executing, usually from insufficient frame allocation relative to its working set.",
    },

    # --- Scheduling ---
    {
        "topic": "Scheduling", "question_type": "mcq", "difficulty_level": 3, "points": 1.5,
        "question_text": "Which CPU scheduling algorithm can cause starvation of long processes?",
        "options": ["FCFS", "Shortest Job First (SJF)", "Round Robin", "None of these"],
        "correct_answer": "Shortest Job First (SJF)",
        "explanation": "SJF always prefers shorter jobs, so a continuous stream of short jobs can starve a long one indefinitely.",
    },
    {
        "topic": "Scheduling", "question_type": "output_prediction", "difficulty_level": 4, "points": 2.5,
        "question_text": "Three processes P1(burst=5), P2(burst=3), P3(burst=1) arrive together. Under SJF (non-preemptive), what is the execution order?",
        "options": None, "correct_answer": "P3, P2, P1",
        "explanation": "SJF picks the shortest remaining burst first among available processes: 1, then 3, then 5.",
    },

    # --- Synchronization / Producer-Consumer ---
    {
        "topic": "Synchronization", "question_type": "mcq", "difficulty_level": 3, "points": 1.5,
        "question_text": "What is the primary purpose of a mutex?",
        "options": [
            "Speed up I/O", "Ensure mutual exclusion to a shared resource",
            "Schedule processes", "Allocate memory",
        ],
        "correct_answer": "Ensure mutual exclusion to a shared resource",
        "explanation": "A mutex (mutual exclusion lock) ensures only one thread/process accesses a critical section at a time.",
    },
    {
        "topic": "Synchronization", "question_type": "case_study", "difficulty_level": 4, "points": 3.0,
        "question_text": "In the classic Producer-Consumer problem with a bounded buffer, explain what goes wrong if you use only a mutex (no semaphores for 'empty'/'full' counts), and why.",
        "options": None,
        "correct_answer": "A mutex alone only prevents simultaneous buffer access — it cannot make a producer wait when the buffer is full, or a consumer wait when it's empty, so you'd need busy-waiting or risk overflow/underflow. Counting semaphores (empty/full) plus a mutex is the standard correct solution.",
        "explanation": "Mutual exclusion and condition synchronization are different problems — a mutex solves the first, not the second.",
    },

    # --- Deadlocks / Banker's Algorithm ---
    {
        "topic": "Deadlocks", "question_type": "multi_select", "difficulty_level": 3, "points": 2.0,
        "question_text": "Which of these are among the four necessary conditions for deadlock? (select all that apply)",
        "options": ["Mutual exclusion", "Hold and wait", "Preemption", "Circular wait", "FIFO scheduling"],
        "correct_answer": ["Mutual exclusion", "Hold and wait", "Circular wait"],
        "explanation": "The four Coffman conditions are: mutual exclusion, hold-and-wait, NO preemption, and circular wait.",
    },
    {
        "topic": "Deadlocks", "question_type": "true_false", "difficulty_level": 3, "points": 1.5,
        "question_text": "The Banker's Algorithm is a deadlock AVOIDANCE strategy, not a deadlock PREVENTION strategy.",
        "options": None, "correct_answer": "true",
        "explanation": "It avoids deadlock by only granting requests that leave the system in a safe state, rather than statically preventing one of the four conditions.",
    },

    # --- Threads / System Calls ---
    {
        "topic": "Threads", "question_type": "mcq", "difficulty_level": 2, "points": 1.0,
        "question_text": "What do threads within the same process typically share?",
        "options": ["Stack only", "Address space and open files", "Nothing", "PID only"],
        "correct_answer": "Address space and open files",
        "explanation": "Threads share the process's memory/address space and file descriptors, but each has its own stack and registers.",
    },
    {
        "topic": "System Calls", "question_type": "mcq", "difficulty_level": 2, "points": 1.0,
        "question_text": "Which system call creates a new process in Unix/Linux?",
        "options": ["exec()", "fork()", "spawn()", "clone_process()"],
        "correct_answer": "fork()",
        "explanation": "`fork()` creates a near-duplicate child process; `exec()` replaces a process's program image, it doesn't create a new process.",
    },

    # --- Disk Scheduling ---
    {
        "topic": "Disk Scheduling", "question_type": "output_prediction", "difficulty_level": 4, "points": 2.5,
        "question_text": "Disk head at track 50. Requests: 82, 170, 43, 140, 24, 16, 190. Under FCFS, what is the first track serviced?",
        "options": None, "correct_answer": "82",
        "explanation": "FCFS (First-Come-First-Served) services requests strictly in arrival order — the first in the list.",
    },

    # --- Dining Philosophers ---
    {
        "topic": "Dining Philosophers", "question_type": "case_study", "difficulty_level": 4, "points": 3.0,
        "question_text": "In the Dining Philosophers problem, explain one classic solution that prevents deadlock, and which Coffman condition it breaks.",
        "options": None,
        "correct_answer": "Having at least one philosopher pick up forks in the opposite order (asymmetric solution) breaks the circular wait condition, preventing deadlock.",
        "explanation": "Other valid answers: limiting philosophers at the table to N-1 (breaks hold-and-wait indirectly), or a resource hierarchy/waiter arbitration solution.",
    },
]


def get_questions_for_topic(topic_name: str) -> list[dict]:
    return [q for q in STATIC_QUESTIONS if q["topic"] == topic_name]


def get_questions_for_topic_and_difficulty(topic_name: str, difficulty_level: int, tolerance: int = 1) -> list[dict]:
    """Returns static-bank questions for a topic within `tolerance` levels
    of the requested difficulty — used by the Question Generator's
    difficulty-based selection (Section 5) so an exact-level miss still
    returns something usable rather than an empty set."""
    return [
        q for q in STATIC_QUESTIONS
        if q["topic"] == topic_name and abs(q["difficulty_level"] - difficulty_level) <= tolerance
    ]


def all_covered_topics() -> list[str]:
    return sorted({q["topic"] for q in STATIC_QUESTIONS})
