import csv
import dataclasses
import time
from pathlib import Path
from typing import List, Optional

import requests
from werkzeug.utils import secure_filename

DUMP_DIRECTORY = Path(__file__).parent / "data"
DUMP_CSV_PATH = DUMP_DIRECTORY / "papers.csv"


@dataclasses.dataclass(frozen=True)
class PaperInfo:
    category_name: str
    title: str
    arxiv_url: str
    pdf_url: str
    code_url: Optional[str]


def main() -> None:
    # 有志によるまとめのmarkdownを取得してきて頑張って論文情報をパースします
    cvpr_papers_url = "https://raw.githubusercontent.com/amusi/CVPR2021-Papers-with-Code/master/README.md"

    r = requests.get(cvpr_papers_url)
    if r.status_code != 200:
        print(f"status code is not 200: {cvpr_papers_url}")
    markdown_lines = r.text.splitlines()

    is_start_category = False
    start_category_prefix = "<a name"
    category_prefix = "# "
    paper_title_prefix = "**"
    paper_url_prefix = "- Paper: "
    code_url_prefix = "- Code: "

    category_name = None
    paper_title = None
    paper_url = None
    code_url = None

    paper_info_list: List[PaperInfo] = []

    # かっこよくmarkdown parser的なのを使いたかったけどいいのがなかったので、各行ごとに見ていってなんとかパースしている
    for markdown_line in markdown_lines:
        if markdown_line.startswith(start_category_prefix):
            is_start_category = True
            continue
        if is_start_category:
            if markdown_line.startswith(category_prefix):
                category_name: str = markdown_line[len(category_prefix) :]
                if "(" in category_name and ")" in category_name:
                    category_name = category_name[
                        category_name.find("(") + 1 : category_name.find(")")
                    ]
            elif markdown_line.startswith(paper_title_prefix):
                if paper_title is not None:
                    pdf_url = paper_url if paper_url.startswith("http") else ""
                    if "arxiv" in pdf_url:
                        pdf_url = pdf_url.replace("abs", "pdf") + ".pdf"
                    paper_info_list.append(
                        PaperInfo(
                            category_name=category_name,
                            title=paper_title,
                            arxiv_url=paper_url,
                            pdf_url=pdf_url,
                            code_url=code_url,
                        )
                    )
                paper_title = markdown_line.replace("**", "")
                paper_url = ""
                code_url = None
            elif markdown_line.startswith(paper_url_prefix):
                paper_url = markdown_line[len(paper_url_prefix) :]
            elif markdown_line.startswith(code_url_prefix):
                code_url = markdown_line[len(code_url_prefix) :]

    # 毎回上書き保存しちゃう
    dump_paper_info_list = [dataclasses.asdict(d) for d in paper_info_list]
    with DUMP_CSV_PATH.open("w") as f:
        dict_writer = csv.DictWriter(f, list(dump_paper_info_list[0].keys()))
        dict_writer.writeheader()
        dict_writer.writerows(dump_paper_info_list)

    # 論文ダウンロード
    errors = []
    for i, paper_info in enumerate(paper_info_list):
        directory = DUMP_DIRECTORY / secure_filename(paper_info.category_name)
        file_path = directory / (secure_filename(paper_info.title) + ".pdf")
        if not directory.is_dir():
            print(f"Make sub directory: {directory}")
            directory.mkdir(parents=True)

        if file_path.is_file():
            print(
                f"{i+1}/{len(paper_info_list)}: {paper_info.title} is already in the directory: {file_path}"
            )
        else:
            if paper_info.pdf_url == "":
                print(
                    f"{i + 1}/{len(paper_info_list)}: {paper_info.title}'s url is unknown. skip"
                )
                continue
            print(
                f"{i+1}/{len(paper_info_list)}: downloading from {paper_info.pdf_url} into {file_path}"
            )
            try:
                r = requests.get(paper_info.pdf_url)
                if r.status_code == 200:
                    with file_path.open("wb") as f:
                        f.write(r.content)
                        f.close()
                        print("downloaded")
                        time.sleep(1)
                else:
                    print("\t download failed")
            except requests.exceptions.SSLError as e:
                print(f"SSL Error: {paper_info.pdf_url}")
                errors.append(paper_info)
            except Exception as e:
                errors.append(paper_info)

    print("Error Lists")
    print(errors)


if __name__ == "__main__":
    main()
