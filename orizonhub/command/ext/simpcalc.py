#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import math
import cmath
import random
import operator
import collections


class CalculatorError(Exception):
    pass


class MathError(CalculatorError):
    '''The Math Error type.'''

    def __init__(self, pos=0, length=1):
        super().__init__(self)
        self.pos = pos
        self.length = length

    def __repr__(self):
        return 'MathError(%s)' % self.pos


class SyntaxError(CalculatorError):
    '''The Syntax Error type.'''

    def __init__(self, pos=0, length=1):
        super().__init__(self)
        self.pos = pos
        self.length = length

    def __repr__(self):
        return 'SyntaxError(%s)' % self.pos


class KbdBreak(CalculatorError):
    '''The Keyboard Break Error type.'''

    def __init__(self, pos=0, length=1):
        super().__init__(self)
        self.pos = pos
        self.length = length

    def __repr__(self):
        return 'KbdBreak(%s)' % self.pos


class Token:

    def __init__(self, name, pos, type, priority=0, argnum=0, value=None):
        self.name = name
        self.pos = pos
        self.type = type
        self.priority = priority
        self.argnum = argnum
        self.value = value

    def __repr__(self):
        return 'Token(%s)' % ', '.join(map(
            repr, (self.name, self.pos, self.type, self.priority, self.argnum, self.value)))


def adapt_cmath(funcname):
    def wrapped(x):
        if isinstance(x, complex):
            return getattr(cmath, funcname)(x)
        else:
            try:
                return getattr(math, funcname)(x)
            except Exception:
                # sqrt etc.
                return getattr(cmath, funcname)(x)
    return wrapped


def gcd(*numbers):
    """Calculate the Greatest Common Divisor of the numbers."""
    if len(numbers) == 2:
        a, b = numbers
        while b:
            a, b = b, a % b
        return a
    elif len(numbers) < 2:
        raise TypeError(
            'gcd expected at least 2 arguments, got ' + str(len(numbers)))
    else:
        val = numbers[0]
        for i in numbers[1:]:
            while i:
                val, i = i, val % i
        return val


def lcm(*numbers):
    """Calculate the Lowest Common Multiple of the numbers."""
    if len(numbers) == 2:
        return numbers[0] * numbers[1] // gcd(numbers[0], numbers[1])
    elif len(numbers) < 2:
        raise TypeError(
            'lcm expected at least 2 arguments, got ' + str(len(numbers)))
    else:
        val = numbers[0]
        for i in numbers[1:]:
            val = val * i // gcd(val, i)
        return val


def resplit(regex, string):
    pos = 0
    for m in regex.finditer(string):
        if m.start(0) != pos:
            yield string[pos:m.start(0)]
        yield string[m.start(0):m.end(0)]
        pos = m.end(0)
    if pos < len(string):
        yield string[pos:]


class Calculator:

    operators = collections.OrderedDict((
        (" ", ('ws', 1, 1)),
        ("\t", ('ws', 1, 1)),
        ("(", ('(', 1, 1)),
        (",", (',', 1, 2)),
        ("!", ('op_l', 2, 1)),
        ("^", ('op_r', 3, 2)),
        ("**", ('op_r', 3, 2)),
        # recognize on parsing
        # ("pos", ('op_r', 4, 1)),
        # ("neg", ('op_r', 4, 1)),
        ("*", ('op_l', 5, 2)),
        ("×", ('op_l', 5, 2)),
        ("/", ('op_l', 5, 2)),
        ("÷", ('op_l', 5, 2)),
        ("\\", ('op_l', 5, 2)),
        ("%", ('op_l', 5, 2)),
        ("+", ('op_l', 6, 2)),
        ("-", ('op_l', 6, 2)),
        (")", (')', 7, 1))
    ))

    const = {
        "i": 1j,
        "pi": math.pi,
        "π": math.pi,
        "e": math.e
    }

    functions = {
        "!": (math.factorial, 1),
        "^": (operator.pow, 2),
        "**": (operator.pow, 2),
        "*": (operator.mul, 2),
        "×": (operator.mul, 2),
        "/": (operator.truediv, 2),
        "÷": (operator.truediv, 2),
        "\\": (operator.floordiv, 2),
        "%": (operator.mod, 2),
        "+": (operator.add, 2),
        "-": (operator.sub, 2),
        "pos": (operator.pos, 1),
        "neg": (operator.neg, 1),
        "abs": (abs, 1),
        "bool": (bool, 1),
        "float": (float, 1),
        "int": (int, 1),
        "max": (max, 2),
        "min": (min, 2),
        "pow": (pow, 2),
        "round": (round, 1),
        "ceil": (math.ceil, 1),
        "copysign": (math.copysign, 2),
        "fabs": (math.fabs, 1),
        "factorial": (math.factorial, 1),
        "floor": (math.floor, 1),
        "fmod": (math.fmod, 1),
        "gcd": (gcd, 2),
        "lcm": (lcm, 2),
        "ldexp": (math.ldexp, 1),
        "trunc": (math.trunc, 1),
        "real": (operator.attrgetter("real"), 1),
        "imag": (operator.attrgetter("imag"), 1),
        "exp": (adapt_cmath("exp"), 1),
        "log": (adapt_cmath("log"), 1),
        "ln": (adapt_cmath("log"), 1),
        "log10": (adapt_cmath("log10"), 1),
        "lg": (adapt_cmath("log10"), 1),
        "sqrt": (adapt_cmath("sqrt"), 1),
        "√": (adapt_cmath("sqrt"), 1),
        "acos": (adapt_cmath("acos"), 1),
        "asin": (adapt_cmath("asin"), 1),
        "atan": (adapt_cmath("atan"), 1),
        "cos": (adapt_cmath("cos"), 1),
        "sin": (adapt_cmath("sin"), 1),
        "tan": (adapt_cmath("tan"), 1),
        "atan2": (math.atan2, 2),
        "hypot": (math.hypot, 2),
        "degrees": (math.degrees, 1),
        "radians": (math.radians, 1),
        "acosh": (adapt_cmath("acosh"), 1),
        "asinh": (adapt_cmath("asinh"), 1),
        "atanh": (adapt_cmath("atanh"), 1),
        "cosh": (adapt_cmath("cosh"), 1),
        "sinh": (adapt_cmath("sinh"), 1),
        "tanh": (adapt_cmath("tanh"), 1),
        "erf": (math.erf, 1),
        "erfc": (math.erfc, 1),
        "gamma": (math.gamma, 1),
        "lgamma": (math.lgamma, 1),
        "phase": (cmath.phase, 1),
        "rect": (cmath.rect, 1),
        "inv": (operator.inv, 1),
        "and": (operator.and_, 2),
        "or": (operator.or_, 2),
        "xor": (operator.xor, 2),
        "rand": (random.random, 0),
        "randrng": (random.uniform, 2),
    }

    ansvar = '_'

    re_float = re.compile(r'([0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?i?)')
    re_delim = re.compile(
        '(%s)' % ('|'.join(map(re.escape, operators.keys()))))
    re_split = re.compile(
        r'([0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?i?|%s)' % ('|'.join(map(re.escape, operators.keys()))))

    def __init__(self, ansvar=None, autoclose=False):
        self.ansvar = ansvar or self.ansvar
        self.vars = {self.ansvar: 0}
        self.autoclose = autoclose

    def splitexpr(self, expr):
        pos = 0
        for s in resplit(self.re_split, expr):
            s = s.lower()
            if not s.strip():
                pass
            elif self.re_float.match(s):
                i = 1
                if s[-1] == 'i':
                    i = 1j
                    s = s[:-1]
                if '.' in s or 'e' in s:
                    yield Token(s, pos, 'num', value=float(s) * i)
                else:
                    yield Token(s, pos, 'num', value=int(s) * i)
            elif self.re_delim.match(s):
                val = self.functions[s][0] if s in self.functions else None
                yield Token(s, pos, *self.operators[s], value=val)
            elif s in self.const:
                yield Token(s, pos, 'const', value=self.const[s])
            elif s in self.vars:
                yield Token(s, pos, 'var')
            elif s in self.functions:
                fn = self.functions[s]
                yield Token(s, pos, 'fn', argnum=fn[1], value=fn[0])
            else:
                raise SyntaxError(pos, len(s))
            pos += len(s)

    def torpn(self, lstin):
        opstack = []
        lastt = None
        for key, token in enumerate(lstin):
            if token.type == '(':
                opstack.append(token)
            elif token.type.startswith('op'):
                if token.name in '+-' and (
                        lastt is None or lastt.type in ('(', 'op_l', 'op_r', ',')):
                    if token.name == '+':
                        token.name = 'pos'
                        token.value = operator.pos
                    else:
                        token.name = 'neg'
                        token.value = operator.neg
                    token.type = 'op_r'
                    token.priority = 0
                    token.argnum = 1
                if opstack:
                    tok2 = opstack[-1]
                    while (tok2.type.startswith('op') and
                           (token.type[-1] == 'l' and token.priority >= tok2.priority or
                            token.type[-1] == 'r' and token.priority > tok2.priority)):
                        yield opstack.pop()
                        if opstack:
                            tok2 = opstack[-1]
                        else:
                            break
                opstack.append(token)
            elif token.type == ',':
                try:
                    while opstack[-1].name != '(':
                        yield opstack.pop()
                except IndexError:
                    raise SyntaxError(key, len(token.name))
            elif token.type == ')':
                try:
                    while opstack[-1].name != '(':
                        yield opstack.pop()
                except IndexError:
                    raise SyntaxError(key, len(token.name))
                op = opstack.pop()
                if opstack and opstack[-1].type == 'fn':
                    yield opstack.pop()
            elif token.type in ('const', 'var'):
                yield token
            elif token.type == 'fn':
                opstack.append(token)
            else:
                yield token
            # check function brackets
            if lastt and token.type != '(' and lastt.type == 'fn' and lastt.argnum:
                raise SyntaxError(lastt.pos, len(lastt.name))
            lastt = token
        while opstack:
            op = opstack.pop()
            if op.type != '(':
                yield op
            # If self.autoclose then ignored right parenthesis is allowed.
            elif not self.autoclose:
                raise SyntaxError(op.pos, len(op.name))

    def evalrpn(self, lstin):
        '''Evaluates the Reverse Polish Expression.'''
        numstack = []
        for token in lstin:
            if token.type in ('num', 'const'):
                numstack.append(token.value)
            elif token.type == 'var':
                numstack.append(self.vars[token.name])
            elif token.type in ('op_l', 'op_r', 'fn'):
                try:
                    args = [numstack.pop() for i in range(token.argnum)]
                except IndexError:
                    raise SyntaxError(token.pos, len(token.name))
                try:
                    numstack.append(token.value(*reversed(args)))
                except KeyboardInterrupt:
                    raise KbdBreak(token.pos, len(token.name))
                except Exception:
                    raise MathError(token.pos, len(token.name))
            else:
                # Logic error in program
                raise AssertionError('token %r appears in RPN' % token)
        if len(numstack) > 1:
            raise SyntaxError(token.pos, len(token.name))
        elif numstack:
            return numstack.pop()
        else:
            return None

    def eval(self, expr):
        ret = self.evalrpn(self.torpn(self.splitexpr(expr)))
        self.vars[self.ansvar] = ret
        return ret

    def format(self, ret):
        if ret is None:
            return ''
        elif isinstance(ret, complex):
            s = str(ret.real) if ret.real else ''
            if ret.imag:
                sign = '+' if ret.imag > 0 and s else ''
                if ret.imag == 1:
                    imag = ''
                elif ret.imag == -1:
                    imag = '-'
                else:
                    imag = str(ret.imag)
                s += sign + imag + 'i'
            elif not ret:
                s = '0'
            return s
        elif ret:
            return str(ret)
        else:
            return '0'

    def pretty(self, expr):
        try:
            return self.format(self.eval(expr))
        except MathError as ex:
            return "Math Error:\n %s\n %s" % (
                expr, ' ' * ex.pos + '^' * ex.length)
        except SyntaxError as ex:
            return "Syntax Error:\n %s\n %s" % (
                expr, ' ' * ex.pos + '^' * ex.length)
        except KbdBreak as ex:
            return "Keyboard Break:\n %s\n %s" % (
                expr, ' ' * ex.pos + '^' * ex.length)


def main():
    calc = Calculator()
    while 1:
        try:
            a = input("> ")
        except (KeyboardInterrupt, EOFError):
            break
        #ret = calc.eval(a)
        ret = calc.pretty(a)
        if ret:
            print(ret)
    print("\b\b", end='')
    return 0

if __name__ == '__main__':
    try:
        import readline
    except ImportError:
        pass
    main()
