from pathlib import Path
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_recent_commits(limit: int = 5) -> dict:
    try:
        result = subprocess.run(
            [
                "git",
                "log",
                f"-{limit}",
                "--pretty=format:%H|%an|%ad|%s",
                "--date=iso",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        commits = []

        for line in result.stdout.splitlines():
            commit_hash, author, date, message = line.split("|", 3)

            commits.append(
                {
                    "hash": commit_hash,
                    "author": author,
                    "date": date,
                    "message": message,
                }
            )

        return {
            "available": True,
            "count": len(commits),
            "commits": commits,
        }

    except subprocess.CalledProcessError as error:
        return {
            "available": False,
            "commits": [],
            "error": error.stderr.strip(),
        }

    except FileNotFoundError:
        return {
            "available": False,
            "commits": [],
            "error": "git command not found",
        }


if __name__ == "__main__":
    print(
        get_recent_commits(limit=5)
    )