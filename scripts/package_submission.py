import os
import shutil
import stat
import zipfile
from pathlib import Path


CODE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = CODE_ROOT.parent
SUBMISSION_FOLDERS = [
    "Synopsis",
    "Input_Data",
    "Code",
    "Model_Prompts_Config",
    "Evaluation_Results",
    "Documentation",
    "Video",
    "Declarations",
]
IGNORED_NAMES = {
    ".env",
    ".git",
    ".pytest_cache",
    ".venv",
    ".venv_clean",
    ".venv_release_test",
    "__pycache__",
    "generate_error_analysis_v4.py",
    "generate_evaluation_pdf_reports.py",
    "generate_independent_verification_artifacts.py",
    "generate_pro_audit_artifacts.py",
}
MIRRORED_ASSETS = [
    "configs/app.yaml",
    "configs/model.yaml",
    "configs/retrieval.yaml",
    "prompts/rag_system_v1.txt",
    "prompts/rag_answer_v1.txt",
    "prompts/entity_extraction_v1.txt",
    "prompts/relationship_extraction_v1.txt",
    "prompts/inconsistency_explanation_v1.txt",
]


def copy_tree_clean(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(f"Required package source directory is missing: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    for item in sorted(source.iterdir()):
        if item.name in IGNORED_NAMES or item.suffix in {".pyc", ".log"}:
            continue
        target = destination / item.name
        if item.is_dir():
            copy_tree_clean(item, target)
        else:
            shutil.copy2(item, target)


def remove_readonly(func, path, error_info) -> None:
    os.chmod(path, stat.S_IWRITE)
    func(path)


def package_submission(
    university: str = "TataUniversity",
    student_name: str = "InternStudent",
    register_no: str = "T03",
) -> Path:
    submission_name = f"{university}_{student_name}_{register_no}_CS1_AIML"
    submission_dir = PROJECT_ROOT / submission_name
    archive_path = PROJECT_ROOT / f"{register_no}_CS1_AIML_v1.0.zip"

    if submission_dir.exists():
        shutil.rmtree(submission_dir, onerror=remove_readonly)
    for folder in SUBMISSION_FOLDERS:
        (submission_dir / folder).mkdir(parents=True, exist_ok=True)

    code_dir = submission_dir / "Code"
    for folder in ["app", "streamlit_app", "scripts", "tests", "configs", "prompts"]:
        copy_tree_clean(CODE_ROOT / folder, code_dir / folder)
    copy_tree_clean(CODE_ROOT / "evaluation", code_dir / "evaluation")

    for filename in ["requirements.txt", "Dockerfile", "docker-compose.yml", ".env.example", ".gitignore", "README.md", "pytest.ini"]:
        source_file = CODE_ROOT / filename
        if source_file.is_file():
            shutil.copy2(source_file, code_dir / filename)

    input_source = PROJECT_ROOT / "Input_Data"
    input_pdfs = sorted(input_source.glob("*.pdf"))
    if len(input_pdfs) < 2:
        raise FileNotFoundError(f"Expected both HLD revision PDFs in {input_source}")
    for pdf_path in input_pdfs:
        shutil.copy2(pdf_path, submission_dir / "Input_Data" / pdf_path.name)

    for folder in ["configs", "prompts"]:
        copy_tree_clean(code_dir / folder, submission_dir / "Model_Prompts_Config" / folder)

    copy_tree_clean(
        CODE_ROOT / "evaluation",
        submission_dir / "Evaluation_Results" / "evaluation",
    )
    copy_tree_clean(PROJECT_ROOT / "Documentation", submission_dir / "Documentation")
    for folder in ["Synopsis", "Video", "Declarations"]:
        copy_tree_clean(PROJECT_ROOT / folder, submission_dir / folder)

    required_docs = [
        "T03_README_v1.0.md",
        "T03_PRD_v1.0.md",
        "T03_Architecture_v1.0.md",
        "T03_API_Documentation_v1.0.md",
        "T03_Test_Report_v1.0.md",
        "FINAL_RUNTIME_PACKAGE_AUDIT_v1.0.md",
    ]
    missing_docs = [name for name in required_docs if not (submission_dir / "Documentation" / name).is_file()]
    if missing_docs:
        raise FileNotFoundError(f"Required release documentation is missing: {', '.join(missing_docs)}")

    if archive_path.exists():
        archive_path.unlink()
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source_file in sorted(path for path in submission_dir.rglob("*") if path.is_file()):
            archive_name = source_file.relative_to(PROJECT_ROOT).as_posix()
            info = zipfile.ZipInfo(archive_name, date_time=(2026, 10, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source_file.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    required_members = [
        f"{submission_name}/Code/requirements.txt",
        f"{submission_name}/Code/pytest.ini",
        f"{submission_name}/Code/app/api/main.py",
        f"{submission_name}/Code/streamlit_app/Home.py",
        f"{submission_name}/Code/scripts/package_submission.py",
        f"{submission_name}/Code/tests/test_api.py",
        f"{submission_name}/Code/evaluation/benchmark_questions_v2.jsonl",
        f"{submission_name}/Documentation/FINAL_RUNTIME_PACKAGE_AUDIT_v1.0.md",
    ]
    excluded_artifacts = []
    absolute_path_files = []
    mirror_mismatches = []
    with zipfile.ZipFile(archive_path, "r") as archive:
        names = set(archive.namelist())
        missing_members = [name for name in required_members if name not in names]
        archive_roots = {name.split("/", 1)[0] for name in names}
        top_level = {
            name.split("/", 1)[1].split("/", 1)[0]
            for name in names
            if name.startswith(f"{submission_name}/") and "/" in name[len(submission_name) + 1:]
        }
        for name in names:
            if any(part in IGNORED_NAMES for part in Path(name).parts):
                excluded_artifacts.append(name)
            if name.startswith(f"{submission_name}/"):
                contents = archive.read(name).decode("utf-8", errors="ignore").lower()
                if "c:\\users\\krish\\onedrive\\desktop\\tata_tech" in contents:
                    absolute_path_files.append(name)
        for relative_path in MIRRORED_ASSETS:
            code_member = f"{submission_name}/Code/{relative_path}"
            mirror_member = f"{submission_name}/Model_Prompts_Config/{relative_path}"
            if code_member not in names or mirror_member not in names or archive.read(code_member) != archive.read(mirror_member):
                mirror_mismatches.append(relative_path)
        corrupt_member = archive.testzip()

    folder_counts = {
        folder: sum(1 for path in (submission_dir / folder).rglob("*") if path.is_file())
        for folder in SUBMISSION_FOLDERS
    }
    if (
        missing_members
        or archive_roots != {submission_name}
        or top_level != set(SUBMISSION_FOLDERS)
        or excluded_artifacts
        or absolute_path_files
        or mirror_mismatches
        or corrupt_member
        or any(count == 0 for count in folder_counts.values())
    ):
        raise RuntimeError(
            "ZIP validation failed: "
            f"missing={missing_members}, top_level={sorted(top_level)}, "
                f"roots={sorted(archive_roots)}, "
            f"excluded={excluded_artifacts}, absolute_paths={absolute_path_files}, "
            f"mirror_mismatches={mirror_mismatches}, corrupt={corrupt_member}, "
            f"folder_counts={folder_counts}"
        )

    print(f"Submission directory: {submission_dir}")
    print(f"Submission ZIP: {archive_path}")
    print(f"Validated top-level folders and runtime assets; file counts: {folder_counts}")
    return archive_path


if __name__ == "__main__":
    package_submission()