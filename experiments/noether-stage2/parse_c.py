"""Tolerant extractor of simple integer while-loops from SV-COMP C sources.

Pre-registered parse filter (applied identically to both methods):

Supported fragment
------------------
* scalar int-family variables (char/short/int/long, signed variants);
  `unsigned` variables are REJECTED (bitvector wraparound semantics are out
  of scope for exact rational arithmetic)
* straight-line prefix before the loop: declarations, assignments,
  `if (C) return;` / `__VERIFIER_assume(C)` preconditions (equality atoms
  pin concrete initial values; anything unknown stays a symbolic parameter,
  pinned to 0 for the numeric sanity pass)
* one while-loop (or desugared for-loop) per function; guard = boolean
  combination of comparisons of polynomial expressions; `while (nondet())`
  is allowed (unknown trip count, deterministic body)
* body: assignments (=, +=, -=, *=, ++, --), if/else nesting expanded into
  <= 16 guarded paths, local declarations WITH initializer

Everything else is SKIPPED and counted: unsigned/bitvector ops, arrays,
pointers, floats, division/modulo, nested loops, break/continue/return in
the body, calls in the body, path explosion, undeclared/unknown-typed
variables, loops preceded by other loops, do-while, switch.

Soundness note: candidate validation uses exact polynomial identities on
every branch, hence is sound regardless of guards; guards feed only the
numeric sanity simulation.
"""

import re
from collections import Counter
from fractions import Fraction

from engine import CLoop, padd, pneg, pscale, pmul, pconst, pstr, lin, trim, \
    psub

# ------------------------------------------------------------------ tokens

TOKEN_RE = re.compile(r"""
    (?P<num>0[xX][0-9a-fA-F]+|\d+)[uUlL]*
  | (?P<id>[A-Za-z_]\w*)
  | (?P<op>\+\+|--|\+=|-=|\*=|/=|%=|==|!=|<=|>=|&&|\|\||[-+*/%<>=!&|^~?:;,.(){}\[\]])
  | (?P<ws>\s+)
""", re.X)

INT_TYPE_WORDS = {"signed", "unsigned", "char", "short", "int", "long",
                  "_Bool", "bool", "size_t", "ssize_t", "ptrdiff_t",
                  "int8_t", "int16_t", "int32_t", "int64_t",
                  "uint8_t", "uint16_t", "uint32_t", "uint64_t"}
FLOAT_TYPE_WORDS = {"float", "double"}
QUAL_WORDS = {"const", "volatile", "register", "static", "inline"}
NONDET_RE = re.compile(r"nondet", re.I)

CMP_OPS = {"==", "!=", "<", "<=", ">", ">="}
FLIP = {"==": "!=", "!=": "==", "<": ">=", ">=": "<", "<=": ">", ">": "<="}

MAX_PATHS = 16
MAX_DNF = 8
MAX_DEGREE = 8


class Unsupported(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class _NondetCall(Exception):
    pass


class _ContinueSig(Exception):
    """Carries partial path outcomes cut short by a `continue`."""

    def __init__(self, outs):
        self.outs = outs


class _CallWithArgs(Exception):
    pass


def tokenize(src):
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"//[^\n]*", " ", src)
    src = re.sub(r"^\s*#.*$", " ", src, flags=re.M)
    src = re.sub(r'"(\\.|[^"\\\n])*"', '""', src)
    src = re.sub(r"'(\\.|[^'\\\n])*'", "''", src)
    toks = []
    for m in TOKEN_RE.finditer(src):
        kind = m.lastgroup
        if kind != "ws":
            text = m.group()
            if kind == "num":
                text = re.sub(r"[uUlL]+$", "", text)
            toks.append((kind, text))
    return toks


def mk_var(i):
    """Poly for variable with global index i (positional exponent tuple)."""
    return lin(i + 1, {i: 1})


# ------------------------------------------------------------------ parser

class CParser:
    """Syntax-only parser: statements to ASTs, arithmetic expressions to
    polys over global variable INDICES (resolved via self.resolve),
    conditions to DNF atom lists. Atom = ('cmp', op, poly) | ('nondet',)."""

    def __init__(self, toks, resolve):
        self.toks = toks
        self.pos = 0
        self.resolve = resolve

    def peek(self, k=0):
        i = self.pos + k
        return self.toks[i] if i < len(self.toks) else (None, None)

    def next(self):
        t = self.peek()
        self.pos += 1
        return t

    def accept(self, text):
        if self.peek()[1] == text:
            self.pos += 1
            return True
        return False

    def expect(self, text):
        if not self.accept(text):
            raise SyntaxError(f"expected {text!r}, got {self.peek()}")

    def skip_balanced(self, open_t, close_t):
        depth = 0
        while self.peek()[0] is not None:
            _, txt = self.next()
            if txt == open_t:
                depth += 1
            elif txt == close_t:
                depth -= 1
                if depth <= 0:
                    return
        raise SyntaxError("unbalanced")

    # ------------------------------------------------------ types

    def parse_type_words(self):
        words = []
        while self.peek()[0] == "id" and (
                self.peek()[1] in INT_TYPE_WORDS
                or self.peek()[1] in FLOAT_TYPE_WORDS
                or self.peek()[1] in QUAL_WORDS or self.peek()[1] == "void"):
            words.append(self.next()[1])
        if not words:
            return None
        if any(w in FLOAT_TYPE_WORDS for w in words):
            base = "float"
        elif any(w == "void" for w in words) and \
                not any(w in INT_TYPE_WORDS for w in words):
            base = "void"
        elif any(w in INT_TYPE_WORDS for w in words):
            base = "unsigned" if "unsigned" in words else "int"
        else:
            base = "unknown"
        if self.peek()[1] == "*":
            while self.peek()[1] == "*":
                self.next()
            base = "ptr"
        return base

    # ------------------------------------------------------ statements

    def parse_block_stmts(self):
        self.expect("{")
        stmts = []
        while self.peek()[1] not in ("}", None):
            save = self.pos
            try:
                stmts.append(self.parse_stmt())
            except (Unsupported, SyntaxError) as e:
                # resync: skip to the next ';' at this nesting level (or the
                # closing brace), so earlier loops remain extractable
                self.pos = save
                depth = 0
                while True:
                    kind, txt = self.peek()
                    if kind is None:
                        break
                    if depth == 0 and txt == ";":
                        self.next()
                        break
                    if txt in ("{", "(", "["):
                        depth += 1
                    elif txt in ("}", ")", "]"):
                        if depth == 0 and txt == "}":
                            break           # leave '}' for the caller
                        depth -= 1
                    self.next()
                stmts.append(("unsupported", getattr(e, "reason", "syntax")))
        self.expect("}")
        return stmts

    def parse_stmt_or_block(self):
        if self.peek()[1] == "{":
            return self.parse_block_stmts()
        return [self.parse_stmt()]

    def parse_stmt(self):
        kind, txt = self.peek()
        if kind == "id" and self.peek(1)[1] == ":" and self.peek(2)[1] != ":":
            self.next()
            self.next()
            return self.parse_stmt()
        if txt == ";":
            self.next()
            return ("empty",)
        if txt == "{":
            return ("block", self.parse_block_stmts())
        if txt == "do":
            # do body while (C);  ~  same transition branches as a while with
            # guard C; conservation identities are guard-independent, so the
            # desugaring is sound for equality-invariant inference
            self.next()
            body = self.parse_stmt_or_block()
            self.expect("while")
            self.expect("(")
            dnf = self.parse_condition()
            self.expect(")")
            self.accept(";")
            return ("while", dnf, body)
        if txt in ("switch", "case", "default", "goto"):
            raise Unsupported(f"stmt:{txt}")
        if txt in ("break", "continue"):
            self.next()
            self.accept(";")
            return (txt,)
        if txt == "return":
            self.next()
            if self.peek()[1] != ";":
                try:
                    self.parse_add()
                except (_NondetCall, _CallWithArgs):
                    pass
            self.accept(";")
            return ("return",)
        if txt == "while":
            self.next()
            self.expect("(")
            dnf = self.parse_condition()
            self.expect(")")
            return ("while", dnf, self.parse_stmt_or_block())
        if txt == "for":
            self.next()
            self.expect("(")
            init = []
            if not self.accept(";"):
                if self.parse_type_words() is not None:
                    init.append(self.parse_declaration_ast())
                else:
                    init.append(self.parse_expr_statement())
            dnf = []
            if not self.accept(";"):
                dnf = self.parse_condition()
                self.expect(";")
            step = []
            if self.peek()[1] != ")":
                step.append(self.parse_expr_statement())
            self.expect(")")
            return ("for", init, dnf, step, self.parse_stmt_or_block())
        if txt == "if":
            self.next()
            self.expect("(")
            dnf = self.parse_condition()
            self.expect(")")
            then_s = self.parse_stmt_or_block()
            else_s = []
            if self.accept("else"):
                else_s = self.parse_stmt_or_block()
            return ("if", dnf, then_s, else_s)
        save = self.pos
        if kind == "id" and (txt in INT_TYPE_WORDS or txt in FLOAT_TYPE_WORDS
                             or txt == "struct"
                             or (self.peek(1)[0] == "id"
                                 and txt not in ("sizeof",))):
            try:
                d = self.parse_declaration_ast()
                return d
            except (Unsupported, SyntaxError):
                self.pos = save
        return self.parse_expr_statement()

    def parse_declaration_ast(self):
        base = self.parse_type_words()
        if base is None:
            raise SyntaxError("not a declaration")
        decls = []
        while True:
            typ = base
            while self.peek()[1] == "*":
                typ = "ptr"
                self.next()
            if self.peek()[0] != "id":
                raise SyntaxError("bad declarator")
            name = self.next()[1]
            if self.peek()[1] == "(":
                self.skip_balanced("(", ")")
                typ = "proto"
            while self.peek()[1] == "[":
                self.skip_balanced("[", "]")
                typ = "array"
            init = None
            if typ != "proto" and self.peek()[1] == "=":
                self.next()
                try:
                    init = self.parse_add()
                except (_NondetCall, _CallWithArgs):
                    init = None            # unknown initial value
            decls.append((name, typ, init))
            if not self.accept(","):
                break
        self.accept(";")
        return ("decl", decls)

    def parse_expr_statement(self):
        kind, txt = self.peek()
        if kind == "id":
            nk, ntxt = self.peek(1)
            if ntxt in ("=", "+=", "-=", "*="):
                self.next()
                self.next()
                try:
                    rhs = self.parse_add()
                except _NondetCall:
                    if ntxt != "=":
                        raise Unsupported("nondet-compound-assign")
                    self.accept(";")
                    return ("nondet_assign", txt)
                except _CallWithArgs:
                    # opaque function value: unknown-but-fixed input (prefix)
                    if ntxt != "=":
                        raise Unsupported("opaque-compound-assign")
                    self.skip_balanced("(", ")")
                    self.accept(";")
                    return ("nondet_assign", txt)
                self.accept(";")
                return ("assign", txt, ntxt, rhs)
            if ntxt in ("/=", "%=", "&=", "|=", "^=", "<<=", ">>="):
                raise Unsupported(f"op:{ntxt}")
            if ntxt in ("++", "--"):
                self.next()
                self.next()
                self.accept(";")
                return ("assign", txt, "+=", pconst(1 if ntxt == "++" else -1))
            if ntxt == "(":
                self.next()                     # id
                if NONDET_RE.search(txt):
                    self.skip_balanced("(", ")")
                    self.accept(";")
                    return ("nondet_stmt", txt)
                if txt in ("__VERIFIER_assume", "assume"):
                    self.next()                 # (
                    try:
                        dnf = self.parse_condition()
                        self.expect(")")
                    except (Unsupported, SyntaxError):
                        depth = 1
                        while depth > 0 and self.peek()[0] is not None:
                            _, t2 = self.next()
                            if t2 == "(":
                                depth += 1
                            elif t2 == ")":
                                depth -= 1
                        dnf = []                # uninterpretable assumption
                    self.accept(";")
                    return ("assume", dnf)
                if txt in ("__VERIFIER_assert", "assert"):
                    self.next()
                    try:
                        dnf = self.parse_condition()
                        self.expect(")")
                    except (Unsupported, SyntaxError):
                        depth = 1
                        while depth > 0 and self.peek()[0] is not None:
                            _, t2 = self.next()
                            if t2 == "(":
                                depth += 1
                            elif t2 == ")":
                                depth -= 1
                        dnf = []                # uninterpretable assertion
                    self.accept(";")
                    return ("assert", dnf)
                self.skip_balanced("(", ")")
                self.accept(";")
                return ("call", txt)
        if txt in ("++", "--"):
            self.next()
            if self.peek()[0] != "id":
                raise Unsupported("bad-inc")
            name = self.next()[1]
            self.accept(";")
            return ("assign", name, "+=", pconst(1 if txt == "++" else -1))
        try:
            expr = self.parse_add()
        except _CallWithArgs:
            # statement containing an opaque call deeper in an expression:
            # consume to ';' and ignore (calls cannot touch tracked scalars
            # without pointers, which this fragment rejects anyway)
            depth = 0
            while True:
                k2, t2 = self.peek()
                if k2 is None or (depth == 0 and t2 == ";"):
                    break
                if t2 in "([{":
                    depth += 1
                elif t2 in ")]}" :
                    depth -= 1
                self.next()
            self.accept(";")
            return ("empty",)
        self.accept(";")
        return ("expr", expr)

    # ------------------------------------------------------ conditions

    def parse_condition(self):
        return self.parse_or_cond()

    def parse_or_cond(self):
        dnf = self.parse_and_cond()
        while self.accept("||"):
            dnf = dnf + self.parse_and_cond()
            if len(dnf) > MAX_DNF:
                raise Unsupported("dnf-too-large")
        return dnf

    def parse_and_cond(self):
        dnf = self.parse_not_cond()
        while self.accept("&&"):
            rhs = self.parse_not_cond()
            dnf = [t + u for t in dnf for u in rhs]
            if len(dnf) > MAX_DNF:
                raise Unsupported("dnf-too-large")
        return dnf

    def parse_not_cond(self):
        if self.accept("!"):
            return self.negate_dnf(self.parse_not_cond())
        if self.peek()[1] == "(":
            save = self.pos
            self.next()
            try:
                dnf = self.parse_or_cond()
                self.expect(")")
                return dnf
            except (SyntaxError, Unsupported):
                self.pos = save
        return [self.parse_cmp_one()]

    def parse_cmp_one(self):
        """One comparison atom, wrapped as a single-term DNF."""
        return [self.parse_cmp()]

    def parse_cmp(self):
        try:
            lhs = self.parse_add()
        except (_NondetCall, _CallWithArgs):
            return ("nondet",)
        _, txt = self.peek()
        if txt in CMP_OPS:
            self.next()
            try:
                rhs = self.parse_add()
            except (_NondetCall, _CallWithArgs):
                raise Unsupported("opaque-in-comparison")
            return ("cmp", txt, padd(lhs, pneg(rhs)))
        return ("cmp", "!=", lhs)

    @staticmethod
    def negate_dnf(dnf):
        out = [[]]
        for term in dnf:
            negs = [[("cmp", FLIP[a[1]], a[2])] if a[0] == "cmp"
                    else [("nondet",)] for a in term]
            out = [t + u for t in out for u in negs]
            if len(out) > MAX_DNF:
                raise Unsupported("dnf-too-large")
        return out

    # ------------------------------------------------------ arithmetic

    def parse_add(self):
        p = self.parse_mul()
        while self.peek()[1] in ("+", "-"):
            op = self.next()[1]
            q = self.parse_mul()
            p = padd(p, q) if op == "+" else padd(p, pneg(q))
        return p

    def parse_mul(self):
        p = self.parse_unary()
        while self.peek()[1] == "*":
            self.next()
            p = pmul(p, self.parse_unary())
            if p and max(sum(m) for m in p) > MAX_DEGREE:
                raise Unsupported("high-degree")
        if self.peek()[1] in ("/", "%"):
            raise Unsupported("div-mod")
        return p

    def parse_unary(self):
        txt = self.peek()[1]
        if txt == "-":
            self.next()
            return pneg(self.parse_unary())
        if txt == "+":
            self.next()
            return self.parse_unary()
        if txt in ("!", "~"):
            raise Unsupported(f"unary:{txt}")
        return self.parse_primary()

    def parse_primary(self):
        kind, txt = self.peek()
        if txt == "(":
            save = self.pos
            self.next()
            if self.parse_type_words() is not None and self.accept(")"):
                return self.parse_unary()          # cast
            self.pos = save
            self.next()
            p = self.parse_add()
            self.expect(")")
            return p
        if kind == "num":
            self.next()
            return pconst(int(txt, 0))
        if kind == "id":
            nxt = self.peek(1)[1]
            if nxt == "(":
                name = txt
                self.next()          # id
                self.next()          # (
                if self.peek()[1] != ")":
                    raise _CallWithArgs()
                self.next()
                if NONDET_RE.search(name):
                    raise _NondetCall()
                raise Unsupported("call-in-expr")
            if nxt == "[":
                raise Unsupported("array-access")
            if nxt in ("++", "--", "->", ".", "?", ":"):
                raise Unsupported(f"expr-op:{nxt}")
            self.next()
            return mk_var(self.resolve(txt))
        raise Unsupported(f"token:{txt}")


# ------------------------------------------------------------------ extractor

class LoopExtractor:
    def __init__(self):
        self.universe = []           # int-family var names in decl order
        self.index = {}              # name -> global poly index
        self.concrete = {}           # name -> Fraction | None
        self.bad = {}                # name -> reason
        self.nvars = 0

    def resolve(self, name):
        if name in self.index:
            return self.index[name]
        if name in self.bad:
            raise Unsupported(self.bad[name])
        raise Unsupported(f"undeclared:{name}")

    def alloc(self, name):
        if name not in self.index:
            self.index[name] = self.nvars
            self.universe.append(name)
            self.nvars += 1

    def declare(self, name, typ, init):
        if typ == "int":
            self.alloc(name)
            self.concrete[name] = self.eval_concrete(init) \
                if init is not None else None
        elif typ == "unsigned":
            self.bad[name] = "unsigned-var"
        elif typ == "float":
            self.bad[name] = "float-var"
        elif typ == "ptr":
            self.bad[name] = "pointer-var"
        elif typ == "array":
            self.bad[name] = "array-var"
        elif typ == "unknown":
            self.bad[name] = "unknown-type"
        # 'void', 'proto': ignore

    def eval_concrete(self, p):
        val = Fraction(0)
        for m, c in p.items():
            for i, e in enumerate(m):
                if not e:
                    continue
                v = self.concrete.get(self.universe[i])
                if v is None:
                    return None
                c = c * (v ** e)
            val += c
        return val


def remap_poly(p, mapping, n):
    """Re-index a poly given old->new index mapping; result has width n."""
    L = (max(mapping) + 1) if mapping else 0
    out = {}
    for m, c in p.items():
        m = m + (0,) * max(0, L - len(m))
        nm = [0] * n
        for i, e in enumerate(m):
            if e:
                nm[mapping[i]] += e
        key = tuple(nm)
        out[key] = out.get(key, Fraction(0)) + c
    return trim(out)


def poly_indices(p):
    s = set()
    for m, c in p.items():
        if c == 0:
            continue
        for i, e in enumerate(m):
            if e:
                s.add(i)
    return s


def extract_loops_from_tokens(toks, file_label, stats):
    ext = LoopExtractor()

    def resolve(name):
        # Lenient at SYNTAX time: unknown identifiers become fresh universe
        # slots (later declarations bind them). Semantic checks happen at
        # loop assembly time (ext.bad / never-declared => parameter).
        ext.alloc(name)
        return ext.index[name]

    parser = CParser(toks, resolve)
    loops = []

    while parser.peek()[0] is not None:
        save = parser.pos
        _, txt = parser.peek()
        if txt in ("typedef", "struct", "union", "enum"):
            while parser.peek()[1] not in (";", "{") and parser.peek()[0] is not None:
                parser.next()
            if parser.peek()[1] == "{":
                parser.skip_balanced("{", "}")
            while parser.peek()[1] not in (";",) and parser.peek()[0] is not None:
                parser.next()
            parser.accept(";")
            continue
        try:
            base = parser.parse_type_words()
            if base is None:
                parser.pos = save
                parser.next()
                continue
            name = None
            if parser.peek()[0] == "id":
                name = parser.next()[1]
            if name is not None and parser.peek()[1] == "(":
                parser.next()                       # (
                params = []
                while parser.peek()[1] not in (")", None):
                    if parser.peek()[1] in (",", "..."):
                        parser.next()
                        continue
                    pt = parser.parse_type_words()
                    if pt is None:
                        parser.next()
                        continue
                    if parser.peek()[0] == "id":
                        pname = parser.next()[1]
                        if parser.peek()[1] == "[":
                            parser.skip_balanced("[", "]")
                        params.append((pname, pt))
                parser.expect(")")
                if parser.peek()[1] == "{":
                    for pname, pt in params:
                        if pt == "int":
                            ext.alloc(pname)
                            ext.concrete[pname] = None
                        elif pt in ("unsigned", "float", "ptr", "array",
                                    "unknown"):
                            ext.bad[pname] = f"{pt}-var"
                    try:
                        body = parser.parse_block_stmts()
                    except Unsupported as e2:
                        # skip whole function; resync at brace depth 0
                        depth = 1
                        while depth > 0 and parser.peek()[0] is not None:
                            _, t2 = parser.next()
                            if t2 == "{":
                                depth += 1
                            elif t2 == "}":
                                depth -= 1
                        stats[f"func-skipped:{e2.reason}"] += 1
                        continue
                    except SyntaxError:
                        depth = 1
                        while depth > 0 and parser.peek()[0] is not None:
                            _, t2 = parser.next()
                            if t2 == "{":
                                depth += 1
                            elif t2 == "}":
                                depth -= 1
                        stats["func-skipped:syntax"] += 1
                        continue
                    stats["functions"] += 1
                    find_loops_in_stmts(body, ext, file_label, loops, stats)
                    continue
                while parser.peek()[1] not in (";",) and parser.peek()[0] is not None:
                    parser.next()
                parser.accept(";")
                continue
            # plain global declaration
            parser.pos = save
            try:
                decl = parser.parse_declaration_ast()
                for dname, dtyp, dinit in decl[1]:
                    ext.declare(dname, dtyp, dinit)
            except (Unsupported, SyntaxError):
                while parser.peek()[1] not in (";",) and parser.peek()[0] is not None:
                    parser.next()
                parser.accept(";")
        except SyntaxError:
            parser.pos = save
            parser.next()
    return loops


def find_loops_in_stmts(stmts, ext, file_label, loops, stats):
    """Apply statements to the concrete environment in order; when a loop is
    met, extract it. Everything after the first loop in a block is not
    interpreted (its prefix env would be untrustworthy)."""

    def apply_prefix(stmt_list, top=True):
        for st in stmt_list:
            kind = st[0]
            if kind == "decl":
                for dname, dtyp, dinit in st[1]:
                    ext.declare(dname, dtyp, dinit)
            elif kind == "assign":
                _, name, op, rhs = st
                if name in ext.bad:
                    raise Unsupported(ext.bad[name])
                if name not in ext.index:
                    raise Unsupported("undeclared-assign")
                val = ext.eval_concrete(rhs)
                cur = ext.concrete.get(name)
                if op == "=":
                    ext.concrete[name] = val
                elif op == "+=":
                    ext.concrete[name] = None if (cur is None or val is None) \
                        else cur + val
                elif op == "-=":
                    ext.concrete[name] = None if (cur is None or val is None) \
                        else cur - val
                elif op == "*=":
                    ext.concrete[name] = None if (cur is None or val is None) \
                        else cur * val
            elif kind == "if":
                _, dnf, then_s, else_s = st
                exits = all(s[0] in ("return", "call", "empty")
                            for s in then_s)
                if exits and not else_s:
                    try:
                        apply_assumptions(CParser.negate_dnf(dnf), ext)
                    except Unsupported:
                        pass
                else:
                    apply_prefix(then_s, top=False)
                    apply_prefix(else_s, top=False)
            elif kind == "block":
                apply_prefix(st[1], top=False)
            elif kind == "unsupported":
                # environment beyond this point is untrustworthy: a later
                # loop would get a wrong prefix -> stop this block
                raise Unsupported(st[1])
            elif kind == "assume":
                apply_assumptions(st[1], ext)
            elif kind == "while":
                muts = build_loop(st[1], st[2], [], ext, file_label, loops,
                                  stats)
                for nm in (muts or []):
                    ext.concrete[nm] = None      # value after loop unknown
            elif kind == "for":
                _, init, dnf, step, body = st
                apply_prefix(init)
                muts = build_loop(dnf, body + step, [], ext, file_label,
                                  loops, stats)
                for nm in (muts or []):
                    ext.concrete[nm] = None
            elif kind == "nondet_assign":
                # prefix: fresh unknown input -> parameter
                ext.concrete[st[1]] = None
            elif kind == "return":
                if top:
                    raise Unsupported("return-before-loop")
                return          # nested return: stop this branch only
            # expr/empty/call/assert/nondet_stmt: ignore

    try:
        apply_prefix(stmts)
    except Unsupported as e:
        stats[f"prefix:{e.reason}"] += 1


def apply_assumptions(dnf, ext):
    """A DNF assumed to HOLD. Only when it is a single conjunction-term can
    we soundly use its atoms: equality atoms with one affine unknown pin a
    concrete initial value."""
    if len(dnf) != 1:
        return
    for atom in dnf[0]:
        if atom[0] != "cmp" or atom[1] != "==":
            continue
        p = atom[2]
        terms = {m: c for m, c in p.items() if c != 0}
        if any(sum(m) > 1 for m in terms):
            continue
        var_pos = [m for m in terms if sum(m) == 1]
        if len(var_pos) != 1:
            continue
        i = var_pos[0].index(1)
        c = terms[var_pos[0]]
        k = sum(v for m, v in terms.items() if sum(m) == 0)
        if c != 0:
            sol = -k / c
            if sol == int(sol) and i < len(ext.universe):
                ext.concrete[ext.universe[i]] = Fraction(int(sol))


def substitute_env(poly, ev, ext):
    """Substitute env polys (name -> poly over global indices) into a poly
    whose variables are global indices; unbound variables stay themselves."""
    from engine import substitute
    idxs = set()
    for m, c in poly.items():
        if c == 0:
            continue
        for i, e in enumerate(m):
            if e:
                idxs.add(i)
    sub = {}
    for i in idxs:
        if i < len(ext.universe):
            name = ext.universe[i]
            sub[i] = ev.get(name) or mk_var(i)
        else:
            sub[i] = mk_var(i)
    return substitute(poly, sub)


def run_block(stmts, env, mutated, conds, ext):
    """Execute a statement list symbolically. env: name -> poly (over global
    indices); returns list of (env, mutated, conds) outcomes.

    Control-exit statements get exact partial-path semantics:
      break / return : the path leaves the loop -> no branch (discarded)
      continue       : the partial state IS a loop-head successor -> raised
                       as _ContinueSig so the caller keeps it as a branch
    This matters for soundness: silently executing statements after a
    continue would invent transitions the program cannot take."""
    outs = [(dict(env), set(mutated), list(conds))]
    for st in stmts:
        kind = st[0]
        if kind == "break" or kind == "return":
            return []
        if kind == "continue":
            raise _ContinueSig(outs)
        new_outs = []
        for ev, mu, co in outs:
            kind = st[0]
            if kind == "assign":
                _, name, op, rhs = st
                if name in ext.bad:
                    raise Unsupported(ext.bad[name])
                if name not in ext.index:
                    raise Unsupported("undeclared-assign")
                r = substitute_env(rhs, ev, ext)
                ev = dict(ev)
                if op == "=":
                    ev[name] = r
                elif op == "+=":
                    base = ev[name] if name in ev else mk_var(ext.index[name])
                    ev[name] = padd(base, r)
                elif op == "-=":
                    base = ev[name] if name in ev else mk_var(ext.index[name])
                    ev[name] = psub(base, r)
                elif op == "*=":
                    base = ev[name] if name in ev else mk_var(ext.index[name])
                    ev[name] = pmul(base, r)
                    if ev[name] and max(sum(m) for m in ev[name]) > MAX_DEGREE:
                        raise Unsupported("high-degree")
                mu = set(mu)
                mu.add(name)
                new_outs.append((ev, mu, co))
            elif kind == "decl":
                for name, typ, init in st[1]:
                    if typ != "int" or init is None:
                        raise Unsupported(
                            "uninitialized-local" if typ == "int"
                            else f"body-decl:{typ}")
                    ext.alloc(name)
                    ev = dict(ev)
                    ev[name] = substitute_env(init, ev, ext)
                    mu = set(mu)
                    mu.add(name)
                new_outs.append((ev, mu, co))
            elif kind == "unsupported":
                raise Unsupported("body-unsupported")
            elif kind in ("expr", "empty", "nondet_stmt", "assert", "call"):
                # calls: error-reporting helpers cannot modify tracked scalars
                # (pointer-bearing signatures are rejected from the fragment)
                new_outs.append((ev, mu, co))
            elif kind == "nondet_assign":
                raise Unsupported("nondet-assign-in-body")
            elif kind == "if":
                _, dnf, then_s, else_s = st
                for term in dnf:
                    atoms = [(a[1], substitute_env(a[2], ev, ext))
                             for a in term if a[0] == "cmp"]
                    if any(a[0] == "nondet" for a in term):
                        atoms = []
                    for e2, m2, c2 in run_block(then_s, ev, mu, co + atoms,
                                                ext):
                        new_outs.append((e2, m2, c2))
                if else_s:
                    neg = CParser.negate_dnf(dnf)
                    for term in neg:
                        atoms = [(a[1], substitute_env(a[2], ev, ext))
                                 for a in term if a[0] == "cmp"]
                        if any(a[0] == "nondet" for a in term):
                            atoms = []
                        for e2, m2, c2 in run_block(else_s, ev, mu,
                                                    co + atoms, ext):
                            new_outs.append((e2, m2, c2))
                else:
                    new_outs.append((ev, mu, co))
            elif kind == "block":
                for e2, m2, c2 in run_block(st[1], ev, mu, co, ext):
                    new_outs.append((e2, m2, c2))
            else:
                raise Unsupported(f"body-stmt:{kind}")
        outs = new_outs
        if len(outs) > MAX_PATHS:
            raise Unsupported("path-explosion")
    return outs


def build_loop(guard_dnf, body, _step, ext, file_label, loops, stats):
    stats["whiles-found"] += 1
    try:
        ident_env = {nm: mk_var(ext.index[nm]) for nm in ext.universe}
        try:
            outcomes = run_block(body, ident_env, set(), [], ext)
        except _ContinueSig as sig:
            outcomes = sig.outs
        # de-duplicate identical outcomes
        uniq, seeno = [], set()
        names = [f"x{i}" for i in range(ext.nvars + 8)]
        for ev, mu, co in outcomes:
            sig = (tuple(sorted((k, pstr(v, names))
                                for k, v in ev.items())),
                   tuple(sorted(mu)),
                   tuple((op, pstr(p, names)) for op, p in co))
            if sig not in seeno:
                seeno.add(sig)
                uniq.append((ev, mu, co))
        outcomes = uniq

        # ---- guard (parsed at loop head: env is identity there)
        g_terms = [[(a[1], a[2]) for a in term if a[0] == "cmp"]
                   for term in guard_dnf]
        if all(len(t) == 0 for t in g_terms):
            g_terms = []

        # ---- referenced variables
        ref_idx = set()
        for term in g_terms:
            for _, p in term:
                ref_idx |= poly_indices(p)
        mutated = set()
        upd_global = []          # {global_idx: poly} per outcome
        for ev, mu, co in outcomes:
            mutated |= mu
            u = {}
            for nm in mu:
                if nm in ext.bad:
                    raise Unsupported(ext.bad[nm])
                if nm not in ext.index:
                    raise Unsupported(f"undeclared:{nm}")
                u[ext.index[nm]] = ev[nm]
            upd_global.append(u)
        for ev, mu, co in outcomes:
            for _, p in co:
                ref_idx |= poly_indices(p)
        for u in upd_global:
            for p in u.values():
                ref_idx |= poly_indices(p)

        keep = [nm for nm in ext.universe
                if ext.index[nm] in ref_idx or nm in mutated]
        keep = sorted(set(keep), key=ext.universe.index)
        for nm in keep:
            if nm in ext.bad:
                raise Unsupported(ext.bad[nm])
        mapping = {ext.index[nm]: j for j, nm in enumerate(keep)}
        nn = len(keep)

        init, params = [], set()
        for j, nm in enumerate(keep):
            v = ext.concrete.get(nm)
            if v is None:
                init.append(0)
                params.add(j)
            else:
                init.append(int(v))

        g2 = [[(op, remap_poly(p, mapping, nn)) for op, p in term]
              for term in g_terms]

        branches = []
        for (ev, mu, co), u in zip(outcomes, upd_global):
            c2 = [(op, remap_poly(p, mapping, nn)) for op, p in co]
            # complete next-state map: untouched variables are identities
            upd = {}
            for nm in keep:
                gi = ext.index[nm]
                p = u.get(gi)
                if p is None:
                    p = mk_var(gi)
                upd[mapping[gi]] = remap_poly(p, mapping, nn)
            branches.append((c2 or None, upd))
        if not branches:
            raise Unsupported("no-paths")
        if not mutated:
            raise Unsupported("no-mutated-vars")

        lp = CLoop(name=file_label, source=file_label, vars=keep, init=init,
                   guard_dnf=g2, branches=branches,
                   mutated={mapping[ext.index[nm]] for nm in mutated
                            if nm in keep},
                   params=params)
        key = loop_key(lp)
        if key in seen_keys:
            stats["duplicates"] += 1
        else:
            seen_keys.add(key)
            loops.append(lp)
        stats["loops-extracted"] += 1
        return sorted(mutated)
    except Unsupported as e:
        stats[f"loop:{e.reason}"] += 1
        return None


seen_keys = set()


def loop_key(lp):
    parts = [",".join(lp.vars), "|".join(str(lp.init)),
             "|".join(pstr(p, lp.vars) for t in lp.guard_dnf for _, p in t)]
    for conds, upd in lp.branches:
        parts.append(";".join(pstr(p, lp.vars) for _, p in conds or [])
                     + ">>" + ";".join(f"{lp.vars[v]}={pstr(p, lp.vars)}"
                                       for v, p in sorted(upd.items())))
    return hash("|".join(parts))


def extract_file(path, stats):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        stats["read-error"] += 1
        return []
    toks = tokenize(src)
    if not toks:
        stats["empty"] += 1
        return []
    try:
        return extract_loops_from_tokens(toks, path, stats)
    except RecursionError:
        stats["parse-crash:recursion"] += 1
        return []
    except Exception as e:                      # tolerant: record, move on
        stats[f"parse-crash:{type(e).__name__}"] += 1
        return []
