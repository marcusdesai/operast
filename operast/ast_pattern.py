
__all__ = ["ASTElem", "Tag", "ast_equals", "ast_repr", "to_pattern"]

import ast
from ast import AST
from itertools import zip_longest
from operast.pattern import *
from typing import Any, Iterator, List, Optional, Set, Tuple, Type, Union


AnyAST = Union[AST, Type[AST]]


class Tag:
    __slots__ = "name", "node"

    def __init__(self, name: str, node: AnyAST) -> None:
        if not (isinstance(node, AST)
                or isinstance(node, type) and issubclass(node, AST)):
            raise ValueError(f"node must be an instance of AST or Type[AST]; found: {node}")
        self.name = name
        self.node = node

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tag):
            return NotImplemented
        return self.name == other.name and ast_equals(self.node, other.node)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Tag('{self.name}', {ast_repr(self.node)})"


ASTElem = Union[AnyAST, Tag]


# noinspection PyProtectedMember
def get_all_ast_fields() -> Set[str]:
    return {field for obj in ast.__dict__.values() if isinstance(obj, type) and
            issubclass(obj, AST) for field in obj._fields}


PY_AST_FIELDS = get_all_ast_fields()


def iter_ast(node: AST) -> Iterator[Tuple[str, Any]]:
    yield from ((k, v) for k, v in node.__dict__.items() if k in PY_AST_FIELDS)


def ast_fields(node: AST) -> List[Tuple[str, Any]]:
    return [(k, v) for k, v in node.__dict__.items() if k in PY_AST_FIELDS]


def tag_elem(item: TreeElem[ASTElem], name: Optional[str] = None) -> TreeElem[ASTElem]:
    if name is None:
        return item
    elif isinstance(item, Tag):
        return item
    elif isinstance(item, Operator):
        if isinstance(item.elem, Tag):
            return item
        item.elem = Tag(name, item.elem)
        return item
    elif isinstance(item, TreePattern):
        pat_range = 1 if isinstance(item, Branch) else len(item.elems)
        for i in range(pat_range):
            sub_elem = item.elems[i]
            if isinstance(sub_elem, TreePattern):
                tag_elem(sub_elem, name)
            else:
                item.elems[i] = Tag(name, sub_elem)
        return item
    else:
        return Tag(name, item)


PatternCheck = Tuple[Optional[TreeElem[ASTElem]], Optional[Any]]


def ast_type_to_pattern(_cls: Type[AST], name: Optional[str]) -> PatternCheck:
    return tag_elem(_cls, name), None


def ast_to_pattern(node: AST, name: Optional[str]) -> PatternCheck:
    and_elems = []
    for field, attr in ast_fields(node):
        opt_pat, opt_any = _to_pattern(attr, field)
        if opt_pat is not None:
            and_elems.append(opt_pat)
        if opt_any is None:
            delattr(node, field)
    tagged = tag_elem(node, name)
    result = Branch(tagged, And(*and_elems)) if and_elems else tagged
    return result, None


def tag_to_pattern(tag: Tag) -> PatternCheck:
    res, _ = _to_pattern(tag.node)
    assert res is not None
    return tag_elem(res, tag.name), None


def branch_to_pattern(branch: Branch[ASTElem], name: Optional[str]) -> PatternCheck:
    for i, sub_elem in enumerate(branch.elems):
        res, _ = _to_pattern(sub_elem)
        assert res is not None
        branch.elems[i] = res
    branch.elems[0] = tag_elem(branch.elems[0], name)
    return branch, None


def fork_pattern_to_pattern(pat: Fork[ASTElem], name: Optional[str]) -> PatternCheck:
    for i, sub_elem in enumerate(pat.elems):
        res, _ = _to_pattern(sub_elem, name)
        assert res is not None
        pat.elems[i] = tag_elem(res, name)
    return pat, None


def operator_to_pattern(op: Operator[ASTElem], name: Optional[str]) -> PatternCheck:
    res, _ = _to_pattern(op.elem, name)
    assert res is not None
    if isinstance(res, Branch):
        assert not isinstance(res[0], (TreePattern, Operator))
        op.elem = res[0]
        res[0] = tag_elem(op, name)
        return res, None
    assert not isinstance(res, TreePattern)
    op.elem = tag_elem(res, name)
    return op, None


def list_to_pattern(lst: List[TreeElem[ASTElem]], name: Optional[str]) -> PatternCheck:
    then_elems = []
    offset = 0
    for i in range(len(lst)):
        opt_pat, opt_any = _to_pattern(lst[offset + i])
        if opt_pat is not None:
            then_elems.append(tag_elem(opt_pat, name))
        if opt_any is None:
            del lst[offset + i:offset + i + 1]
            offset -= 1
    any_res = lst if lst else None
    result = Then(*then_elems) if then_elems else None
    return result, any_res


def _to_pattern(item: Any, name: Optional[str] = None) -> PatternCheck:
    if isinstance(item, type) and issubclass(item, AST):
        return ast_type_to_pattern(item, name)
    elif isinstance(item, AST):
        return ast_to_pattern(item, name)
    elif isinstance(item, Tag):
        return tag_to_pattern(item)
    elif isinstance(item, Branch):
        return branch_to_pattern(item, name)
    elif isinstance(item, Fork):
        return fork_pattern_to_pattern(item, name)
    elif isinstance(item, Operator):
        return operator_to_pattern(item, name)
    elif isinstance(item, list):
        return list_to_pattern(item, name)
    else:
        return None, item


def to_pattern(elem: TreeElem[ASTElem]) -> TreeElem[ASTElem]:
    result, _ = _to_pattern(elem)
    assert result is not None
    return result


def ast_equals(elem_a: AnyAST, elem_b: AnyAST) -> bool:
    if isinstance(elem_a, AST) and isinstance(elem_b, AST):
        zipped = zip_longest(iter_ast(elem_a), iter_ast(elem_b), fillvalue=None)
        return type(elem_a) is type(elem_b) and all(i == j for i, j in zipped)
    return elem_a is elem_b


def ast_repr(elem: AnyAST) -> str:  # pragma: no cover
    if isinstance(elem, AST):
        field_reprs = ', '.join(f'{f}={repr(v)}' for f, v in iter_ast(elem))
        return f'{type(elem).__name__}({field_reprs})'
    return elem.__name__


__EXTENSIONS.update({
    AST: {
        EXT_EQUALS: ast_equals,
        EXT_REPR: ast_repr,
    }
})
