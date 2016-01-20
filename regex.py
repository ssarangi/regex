"""
The MIT License (MIT)

Copyright (c) 2015 <Satyajit Sarangi>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

RegexOpPrecedence = {
                     '(' : 1,
                     '|' : 2,
                     '.' : 3,
                     '?' : 4,
                     '*' : 4,
                     '+' : 4,
                     '^' : 5
                     }

def get_precedence(char, op_precedence):
    if char in op_precedence:
        return op_precedence[char]

    return 6

def get_right_associativity(char, op_precedence):
    prec = 6
    if char in op_precedence:
        prec = op_precedence[char]

    return prec < 0

def take_while(list, lamda_fn):
    new_list = []
    for item in reversed(list):
        if lamda_fn(item):
            new_list.append(item)
        else:
            break

    return new_list

def format_regex(regex, result):
    all_operators = ['|', '?', '+', '*', '^']
    binary_operators = ['^', '|']

    if regex == "":
        return result

    c1 = regex[0]

    if len(regex[1:]) > 0:
        c2 = regex[1:][0]
    else:
        c2 = ' '

    c2_in_all_operators = c2 in all_operators
    c1_in_binary_operators = c1 in binary_operators

    tmp = ""
    if c1 != '(' and c2 != ')' and c2 != ' ' and not c2_in_all_operators and not c1_in_binary_operators:
        tmp = "."

    v = format_regex(regex[1:], result + c1 + tmp)
    return v

# ., a, b (Any Literal)
class Literal:
    def __init__(self, c):
        self.c = c

    def __eq__(self, other):
        return self.c == other.c

    def __str__(self):
        str = "Literal(%s)" % self.c
        return str

    __repr__ = __str__

# a|b
class Or:
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def __eq__(self, other):
        return self.lhs == other.lhs and self.rhs == other.rhs

    def __str__(self):
        str = "Or(%s, %s)" % (str(self.lhs), str(self.rhs))
        return str

    __repr__ = __str__


# ab. -> Concatenation of a & b. Need to find a better way to represent concatenation
class Concat:
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def __eq__(self, other):
        return self.lhs == other.lhs and self.lhs == other.rhs

    def __str__(self):
        str = "Concat(%s, %s)" % (str(self.lhs), str(self.rhs))
        return str

    __repr__ = __str__


# a* -> Zero or more elements of a
class Repeat:
    def __init__(self, expr):
        self.expr = expr

    def __eq__(self, other):
        return self.expr == other.expr

    def __str__(self):
        str = "Repeat(%s)" % str(self.expr)
        return str

    __repr__ = __str__


# a+ -> One or more elements of a. This can be optimized to Concat(a, Repeat(a)) but for now I want to keep a separate
# case class for it.
class Plus:
    def __init__(self, expr):
        self.expr = expr

    def __eq__(self, other):
        return self.expr == other.expr

    def __str__(self):
        str = "Plus(%s)" % str(self.expr)
        return str

    __repr__ = __str__


def infix2postfix(input, op_stack = [], postfix_prev_iter = ""):
    postfix = postfix_prev_iter
    stack = op_stack

    if input == "":
        stack.reverse()
        return postfix + "".join(stack)

    c = input[0]

    if c == '(':
        stack.append(c)
    elif c == ')':
        not_eq_lambda = lambda x: x != '('
        stack_elems_to_pop = take_while(stack, not_eq_lambda)
        postfix += ''.join(stack_elems_to_pop)
        stack = stack[:len(stack) - len(stack_elems_to_pop) + 1]
    else:
        cPrecedence = get_precedence(c, RegexOpPrecedence)
        lambda_t = lambda x: get_precedence(x, RegexOpPrecedence) >= cPrecedence and get_right_associativity(x, RegexOpPrecedence) == False
        stack_to_take = take_while(stack, lambda_t)
        postfix += "".join(stack_to_take)
        stack = stack[:len(stack) - len(stack_to_take)]
        stack.append(c)

    v = infix2postfix(input[1:], stack, postfix)
    return v

def postfix2tree(postfix):
    stack = []

    for x in postfix:
        if x == '.':
            rhs = stack.pop()
            lhs = stack.pop()
            concat_expr = Concat(lhs, rhs)
            stack.append(concat_expr)
        elif x == '*':
            top_expr = stack.pop()
            repeat_expr = Repeat(top_expr)
            stack.append(repeat_expr)
        elif x == '+':
            top_expr = stack.pop()
            plus_expr = Plus(top_expr)
            stack.append(plus_expr)
        elif x == '|':
            rhs = stack.pop()
            lhs = stack.pop()
            or_expr = Or(lhs, rhs)
            stack.append(or_expr)
        else:
            expr = Literal(x)
            stack.append(expr)

    assert len(stack) == 1
    return stack.pop()

class State: pass

class Consume(State):
    def __init__(self, c, out):
        self.c = c
        self.out = out

class Split(State):
    def __init__(self, out1, out2):
        self.out1 = out1
        self.out2 = out2

class PlaceHolder(State):
    def __init__(self, pointing_to):
        self.pointing_to = pointing_to

class Match(State): pass


def regex_to_nfa(regex, next_state):
    if isinstance(regex, Literal):
        return Consume(regex.c, next_state)

    elif isinstance(regex, Concat):
        return regex_to_nfa(regex.lhs, regex_to_nfa(regex.rhs, next_state))

    elif isinstance(regex, Or):
        s = Split(regex_to_nfa(regex.lhs, next_state), regex_to_nfa(regex.rhs, next_state))
        return s

    elif isinstance(regex, Repeat):
        placeholder = PlaceHolder(None)
        split = Split(regex_to_nfa(regex.expr, placeholder), next_state)
        placeholder.pointing_to = split
        return placeholder

    elif isinstance(regex, Plus):
        return regex_to_nfa(Concat(regex.expr, Repeat(regex.expr)), next_state)


class Regex:
    def __init__(self):
        self.nfa = None

    def compile(self, regex_str):
        postfix_regex = infix2postfix(format_regex(regex_str, ""), [])

        postfix_tree = postfix2tree(postfix_regex)

        self.nfa = regex_to_nfa(postfix_tree, Match())

    def evaluate_nfa_recursive(self, root, string_to_match):
        if isinstance(root, Match):
            if string_to_match == "":
                return True
            else:
                return False

        elif isinstance(root, Split):
            dir1 = self.evaluate_nfa_recursive(root.out1, string_to_match)
            dir2 = self.evaluate_nfa_recursive(root.out2, string_to_match)
            return dir1 | dir2

        elif isinstance(root, Consume):
            if string_to_match == "":
                return False
            elif root.c != string_to_match[0]:
                return False
            else:
                return self.evaluate_nfa_recursive(root.out, string_to_match[1:])

        elif isinstance(root, PlaceHolder):
            return self.evaluate_nfa_recursive(root.pointing_to, string_to_match)

    def matches(self, string_to_match):
        return self.evaluate_nfa_recursive(self.nfa, string_to_match)


def main():
    compiled_regex = Regex()
    compiled_regex.compile("ab*|c+d")
    matches = compiled_regex.matches("ccccccccccd")
    print(matches)

if __name__ == "__main__":
    main()