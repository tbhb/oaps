---
name: refactoring
title: Refactoring standard
description: Safe refactoring process, code smell identification, common refactoring patterns. Load when improving existing code.
commands:
  uv run pytest: Run tests after each refactoring change
  uv run pytest --cov: Verify coverage before refactoring
  uv run basedpyright: Type check after refactoring
  uv run ruff check .: Lint after refactoring
  just lint && just test: Full verification after refactoring
  git diff: Review changes before committing
  git status: Check modified files
principles:
  - Make small changes one refactoring at a time
  - Ensure test coverage before refactoring
  - Run tests after each change to verify behavior preserved
  - Commit frequently for easy rollback
  - No behavior changes unless intentional
best_practices:
  - '**Extract methods**: Extract methods from long functions to improve focus'
  - '**Extract common logic**: Extract common logic to eliminate duplicate code'
  - '**Group parameters**: Use dataclass or TypedDict to group long parameter lists'
  - '**Move methods**: Move methods to classes they use most to reduce feature envy'
  - '**Replace conditionals**: Replace conditionals with polymorphism for type-based behavior'
  - '**Introduce parameter objects**: Introduce parameter objects for related arguments'
checklist:
  - Tests exist with >95% coverage
  - One refactoring at a time
  - Tests pass after each change
  - No behavior changes (unless intentional)
  - Commits are small and focused
references:
  https://refactoring.guru/refactoring: Refactoring patterns and techniques
---

## Safe refactoring process

1. **Ensure test coverage** - **MUST** have >95% coverage before refactoring
1. **Make small changes** - One refactoring at a time
1. **Run tests after each change** - Verify behavior preserved
1. **Commit frequently** - Easy rollback if needed

## Code smells to address

### Long functions

Split into smaller, focused functions:

```python
# Before: too much in one function
def process_order(order: Order) -> None:
    # validation
    # pricing calculation
    # inventory update
    # notification
    ...


# After: separated concerns
def process_order(order: Order) -> None:
    validate_order(order)
    calculate_pricing(order)
    update_inventory(order)
    send_notification(order)
```

### Duplicate code

Extract common logic:

```python
# Before: duplicated validation
def create_user(email: str) -> User:
    if "@" not in email:
        raise ValueError("Invalid email")
    ...


def update_email(user: User, email: str) -> None:
    if "@" not in email:
        raise ValueError("Invalid email")
    ...


# After: extracted function
def validate_email(email: str) -> str:
    if "@" not in email:
        raise ValueError("Invalid email")
    return email


def create_user(email: str) -> User:
    email = validate_email(email)
    ...
```

### Long parameter lists

Use dataclass or TypedDict:

```python
# Before: too many parameters
def create_report(
    title: str,
    author: str,
    date: datetime,
    format: str,
    include_charts: bool,
    include_tables: bool,
) -> Report: ...


# After: grouped into dataclass
@dataclass(frozen=True, slots=True)
class ReportConfig:
    title: str
    author: str
    date: datetime
    format: str
    include_charts: bool = True
    include_tables: bool = True


def create_report(config: ReportConfig) -> Report: ...
```

### Feature envy

Move method to class it uses most:

```python
# Before: Calculator uses Order's data extensively
class Calculator:
    def calculate_total(self, order: Order) -> float:
        return sum(item.price * item.quantity for item in order.items) + order.shipping


# After: move to Order
class Order:
    def calculate_total(self) -> float:
        return sum(item.price * item.quantity for item in self.items) + self.shipping
```

## Common refactoring patterns

### Extract method

```python
# Before
def process(data: list[dict]) -> list[Result]:
    results = []
    for item in data:
        # Complex transformation logic
        transformed = ...
        results.append(transformed)
    return results


# After
def process(data: list[dict]) -> list[Result]:
    return [transform_item(item) for item in data]


def transform_item(item: dict) -> Result:
    # Transformation logic here
    ...
```

### Replace conditional with polymorphism

```python
# Before
def calculate_price(product_type: str, base: float) -> float:
    if product_type == "standard":
        return base
    elif product_type == "premium":
        return base * 1.5
    elif product_type == "discount":
        return base * 0.8


# After
class Product(Protocol):
    def calculate_price(self, base: float) -> float: ...


class StandardProduct:
    def calculate_price(self, base: float) -> float:
        return base


class PremiumProduct:
    def calculate_price(self, base: float) -> float:
        return base * 1.5
```

### Introduce parameter object

```python
# Before
def search(
    query: str,
    limit: int,
    offset: int,
    sort_by: str,
    sort_order: str,
) -> list[Result]: ...


# After
@dataclass(frozen=True, slots=True)
class SearchParams:
    query: str
    limit: int = 10
    offset: int = 0
    sort_by: str = "relevance"
    sort_order: str = "desc"


def search(params: SearchParams) -> list[Result]: ...
```
