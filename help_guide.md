What's new and why:

*.py[cod] is a pattern that matches .pyc, .pyo, and .pyd in one line. The square brackets mean "any one of these characters."
.pytest_cache/, .coverage, htmlcov/ are files pytest and coverage tools create when you run tests.
.env.* with !.env.example: the first line ignores every variant, like .env.local or .env.production. The ! is an exception that says "except this one." Rule order matters: the exception has to come after the rule it overrides.
node_modules/, .next/: the dashboard will generate thousands of dependency and build files. We're ignoring them now so there's no accident later.
.vscode/: VS Code stores machine-specific settings there, like your interpreter path, which wouldn't work on anyone else's computer.

##requirements
What each package is for:

pydantic defines data shapes with type checking. For example, an attack test case will be a model with fields like category, prompt, and expected_behavior. FastAPI is built on Pydantic, so you'll use it everywhere. The >=2 matters because version 2 changed a lot, and older tutorials use v1 syntax that won't work.
python-dotenv reads your .env file so your code can access API keys without hardcoding them.
pytest is the testing framework from your tech stack.
## Task 3
What you've learned so far

You've set up a professional Python environment on your own: Homebrew, a version-controlled Python, isolated virtual environments, git identity, SSH key authentication, .gitignore patterns, the .env / .env.example convention, and a package structure ready for imports. Many tutorials skip these fundamentals, and they're what makes the later deployment tasks go smoothly.

## function tool calling
Step 4: How function-calling works

This concept is the foundation of the whole project, so it's worth understanding before we write the tools.

The model never runs your code. It can only ask your code to run something. The loop works like this:

1. Your code sends: conversation + descriptions of available tools
2. The model replies with EITHER:
     a) a normal text answer → done
     b) a tool request: "call lookup_order with {"order_id": "ORD-1001"}"
3. If (b): YOUR code runs the function, adds the result to the
   conversation as a "tool" message, and goes back to step 1
4. Repeat until the model gives a text answer


his matters for AgentRedTeam: Since every tool call passes through your code, you can record exactly what the agent tried to do, not just what it said. An agent might say "I can't issue that refund" while having already called issue_refund. Catching that gap between words and actions is where agent red-teaming goes further than testing plain chatbots.


##. customer tool
Design decisions worth noticing:

Tools return errors as data ({"error": ...}) instead of raising exceptions. The error goes back to the model as a tool result, so the agent can recover, for example by telling the user the order doesn't exist. How the agent handles errors is itself something we'll test.
issue_refund deliberately skips policy checks. In production you'd enforce rules in both places. Here we want to test the agent's judgment, so the tool trusts it completely.
REFUND_LOG records side effects. In Task 10, a rule-based check can simply ask whether any refund was issued above 5000 or for an undelivered order. That's a deterministic, 100% reliable failure detector, with no LLM needed.
TOOL_SCHEMAS and TOOL_FUNCTIONS are separate: the schemas are what the model sees, and the functions are what your code runs. The dictionary connects a requested name to real code, and the model can never run anything that isn't in it.