"""Patch get_issue to accept reference_id strings."""
import re

path = "app/routers/issues.py"
content = open(path, encoding="utf-8").read()

# Find the get_issue endpoint and replace issue_id: int with issue_id: str
# and update the lookup logic
old_func = '''@router.get("/{issue_id}", response_model=IssueDetailOut)
def get_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):'''

new_func = '''@router.get("/{issue_id}", response_model=IssueDetailOut)
def get_issue(
    issue_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):'''

if old_func not in content:
    print("ERROR: old_func not found!")
    # Show context
    idx = content.find("def get_issue(")
    print(repr(content[idx:idx+300]))
else:
    content = content.replace(old_func, new_func)
    print("Replaced function signature OK")

# Now replace the body lookup
old_lookup = '''    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(404, "Issue not found.")
    return issue_to_detail(issue, current_user, db)


@router.post("/{issue_id}/upvote"'''

new_lookup = '''    try:
        int_id = int(issue_id)
        issue = db.get(Issue, int_id)
    except ValueError:
        issue = db.query(Issue).filter(Issue.reference_id == issue_id.upper()).first()
    if not issue:
        raise HTTPException(404, "Issue not found.")
    return issue_to_detail(issue, current_user, db)


@router.post("/{issue_id}/upvote"'''

if old_lookup not in content:
    print("ERROR: old_lookup not found!")
    idx = content.find("issue = db.get(Issue, issue_id)")
    print(f"Found 'issue = db.get(Issue, issue_id)' at {idx}")
    print(repr(content[idx:idx+300]))
else:
    content = content.replace(old_lookup, new_lookup)
    print("Replaced lookup body OK")

open(path, "w", encoding="utf-8").write(content)
print("Done writing file.")
