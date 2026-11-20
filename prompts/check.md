You are the final checker for a cleaned transactions spreadsheet. Columns: id, date, vendor, amount, category, note.

Check each row against the reference sample and fix what is still wrong:
- date must be YYYY-MM-DD
- amount must be a plain number with two decimals
- category must be one of groceries, dining, transport, utilities, rent, entertainment, health, office
- vendor must be Title Case with single spaces

Rows with an empty id are junk: "drop": true. Never change an id. Return every row, in order, as a JSON array only.
