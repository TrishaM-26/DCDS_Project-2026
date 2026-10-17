"""Create the indexes used by the waste module.

Run once from the project root:   python -m seed.create_indexes
Safe to run again: MongoDB ignores an index that already exists.
"""
from modules.waste import setup_indexes, WasteDBError


def main():
    try:
        names = setup_indexes()
    except WasteDBError as exc:
        print(f"Could not create indexes: {exc}")
        return
    print("Indexes ready:", ", ".join(names))


if __name__ == "__main__":
    main()
