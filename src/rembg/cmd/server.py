import argparse
import glob
import logging
import os
from io import BytesIO

from flask import Flask, request, send_file
from waitress import serve

from ..bg import remove

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    if "Apikey" not in request.headers.keys():
        error = f"Авторизация не удалась: не найден ключ API, {list(request.headers.keys())}"

        logger.error(error)

        return {
            "error": error
        }, 401

    if request.headers["Apikey"] != os.environ["API_KEY"]:
        error = "Авторизация не удалась: ключ API не подошел"

        logger.error(error)

        return {"error":  "Авторизация не удалась: ключ API не подошел"}, 401

    file_content = ""

    if request.method == "POST":
        if "file" not in request.files:
            error = "В запросе не передан обязательный параметр 'file'"

            logger.error(error)

            return {"error": error}, 400

        file_content = request.files["file"].read()

    if request.method == "GET":
        error = "GET запросы не поддерживаются сервисом"

        logger.error(error)

        return {"error": error}, 405

    if file_content == "":
        error = "Содержимое файла оказалось пустым"

        logger.error(error)

        return {"error": error}, 400

    alpha_matting = "a" in request.values
    af = request.values.get("af", type=int, default=240)
    ab = request.values.get("ab", type=int, default=10)
    ae = request.values.get("ae", type=int, default=10)
    az = request.values.get("az", type=int, default=1000)

    model = request.args.get("model", type=str, default="u2net")
    model_path = os.environ.get(
        "U2NETP_PATH",
        os.path.expanduser(os.path.join("~", ".u2net")),
    )
    model_choices = [
        os.path.splitext(os.path.basename(x))[0]
        for x in set(glob.glob(model_path + "/*"))
    ]

    model_choices = list(set(model_choices + ["u2net", "u2netp", "u2net_human_seg"]))

    if model not in model_choices:
        error = f"Некорректный параметр 'model'. Доступные значения – {model_choices}"

        logger.error(error)

        return {
            "error": error
        }, 400

    try:
        return send_file(
            BytesIO(
                remove(
                    file_content,
                    model_name=model,
                    alpha_matting=alpha_matting,
                    alpha_matting_foreground_threshold=af,
                    alpha_matting_background_threshold=ab,
                    alpha_matting_erode_structure_size=ae,
                    alpha_matting_base_size=az,
                )
            ),
            mimetype="image/png",
        )
    except Exception as e:
        app.logger.exception(e, exc_info=True)

        return {"error": "Что-то пошло не так"}, 500


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "-a",
        "--addr",
        default="0.0.0.0",
        type=str,
        help="The IP address to bind to.",
    )

    ap.add_argument(
        "-p",
        "--port",
        default=5000,
        type=int,
        help="The port to bind to.",
    )

    args = ap.parse_args()
    serve(app, host=args.addr, port=args.port)


if __name__ == "__main__":
    main()
