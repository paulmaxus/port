import port.api.props as props
from port.api.commands import (CommandSystemDonate, CommandSystemExit, CommandUIRender)

import pandas as pd
import zipfile
import json


def process(sessionId):
    yield donate(f"{sessionId}-tracking", '[{ "message": "user entered script" }]')

    key = "zip-contents-example"
    meta_data = []
    meta_data.append(("debug", f"{key}: start"))

    # STEP 1: select the file
    data = None
    while True:
        meta_data.append(("debug", f"{key}: prompt file"))
        promptFile = prompt_file("application/zip, text/plain")
        fileResult = yield render_donation_page(promptFile)
        if fileResult.__type__ == 'PayloadString':
            meta_data.append(("debug", f"{key}: extracting file"))
            extractionResult = extract_instagram_posts(fileResult.value)
            if extractionResult != 'invalid':
                meta_data.append(("debug", f"{key}: extraction successful, go to consent form"))
                data = extractionResult
                break
            else:
                meta_data.append(("debug", f"{key}: prompt confirmation to retry file selection"))
                retry_result = yield render_donation_page(retry_confirmation())
                if retry_result.__type__ == 'PayloadTrue':
                    meta_data.append(("debug", f"{key}: skip due to invalid file"))
                    continue
                else:
                    meta_data.append(("debug", f"{key}: retry prompt file"))
                    break

    # STEP 2: ask for consent
    if data is not None:
        meta_data.append(("debug", f"{key}: prompt consent"))
        prompt = prompt_consent(data, meta_data)
        consent_result = yield render_donation_page(prompt)
        if consent_result.__type__ == "PayloadJSON":
            meta_data.append(("debug", f"{key}: donate consent data"))
            yield donate(f"{sessionId}-{key}", consent_result.value)

    yield exit(0, "Success")


def render_donation_page(body):
    header = props.PropsUIHeader(props.Translatable({
        "en": "Instagram flow",
        "nl": "Port voorbeeld flow"
    }))

    page = props.PropsUIPageDonation("Zip", header, body, None)
    return CommandUIRender(page)


def retry_confirmation():
    text = props.Translatable({
        "en": "Unfortunately, we cannot process your file. Continue, if you are sure that you selected the right file. Try again to select a different file.",
        "nl": "Helaas, kunnen we uw bestand niet verwerken. Weet u zeker dat u het juiste bestand heeft gekozen? Ga dan verder. Probeer opnieuw als u een ander bestand wilt kiezen."
    })
    ok = props.Translatable({
        "en": "Try again",
        "nl": "Probeer opnieuw"
    })
    cancel = props.Translatable({
        "en": "Continue",
        "nl": "Verder"
    })
    return props.PropsUIPromptConfirm(text, ok, cancel)


def prompt_file(extensions):
    description = props.Translatable({
        "en": "Please select an Instagram zip file stored on your device.",
        "nl": "Selecteer een Instagram zip file die u heeft opgeslagen op uw apparaat."
    })

    return props.PropsUIPromptFileInput(description, extensions)


def extract_instagram_posts(filename):
    data = extract_content_from_zip(filename, 'media.json')
    if data and (data != 'invalid'):
        posts = [(len(data.get('stories', [])), len(data.get('photos', [])))]
        return posts
    else:
        return data


def extract_content_from_zip(filename, fn_content):
    try:
        data = None
        with zipfile.ZipFile(filename) as zf:
            with zf.open(fn_content) as cf:
                data = json.loads(cf.read())
        return data
    except zipfile.error:
        return "invalid"


def prompt_consent(data, meta_data):

    table_title = props.Translatable({
        "en": "Number of posts on Instagram",
        "nl": "Aantal posts op Instagram"
    })

    log_title = props.Translatable({
        "en": "Log messages",
        "nl": "Log berichten"
    })

    data_frame = pd.DataFrame(data, columns=["Stories", "Photos"])
    table = props.PropsUIPromptConsentFormTable("zip_content", table_title, data_frame)
    return props.PropsUIPromptConsentForm([table], [])


def donate(key, json_string):
    return CommandSystemDonate(key, json_string)


def exit(code, info):
    return CommandSystemExit(code, info)
