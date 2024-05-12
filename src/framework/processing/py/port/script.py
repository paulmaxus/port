import port.api.props as props
from port.api.commands import (CommandSystemDonate, CommandSystemExit, CommandUIRender)

import pandas as pd
import zipfile
import json


def process(session_id):
    data = None
    while True:
	# require participant to provide instagram zip file
        zip_file_prompt = prompt_file("application/zip")
        zip_file_result = yield render_donation_page(zip_file_prompt)
        if zip_file_result.__type__ == 'PayloadString':
            # unzip and extract data
            extraction_result = extract_instagram_posts(zip_file_result.value)
            if extraction_result != 'invalid':
                data = extraction_result
                break
            else:
		# let participant choose to retry upon failure
                retry_result = yield render_donation_page(retry_confirmation())
                if retry_result.__type__ == 'PayloadTrue':
                    continue
                else:
                    break
    # ask for consent to donate extracted data
    if data is not None:
        consent_prompt = prompt_consent(data)
        consent_result = yield render_donation_page(consent_prompt)
        if consent_result.__type__ == "PayloadJSON":
            yield donate(f"{session_id}", consent_result.value)
    # show final page
    yield exit()


def render_donation_page(body):
    header = props.PropsUIHeader(props.Translatable({
        "en": "Instagram data donation",
        "nl": "Instagram data donatie"
    }))
    page = props.PropsUIPageDonation("Zip", header, body, None)
    return CommandUIRender(page)


def retry_confirmation():
    text = props.Translatable({
        "en": "Unfortunately, we cannot process your file. Continue if you are sure that you selected the right file. Try again to select a different file.",
        "nl": "Helaas kunnen we uw bestand niet verwerken. Weet u zeker dat u het juiste bestand heeft gekozen? Ga dan verder. Probeer opnieuw als u een ander bestand wilt kiezen."
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
    # all post types are listed in media.json: extract and count
    data = extract_content_from_zip(filename, 'media.json')
    if data and (data != 'invalid'):
        # exclude profile (=1)
        posts = [(k,len(l)) for k,l in data.items() if k!='profile']
        return posts
    else:
        return data


def extract_content_from_zip(filename, fn_content):
    # extract (json) data from file in zip
    try:
        data = None
        with zipfile.ZipFile(filename) as zf:
            try:
                with zf.open(fn_content) as cf:
                    data = json.loads(cf.read())
            except KeyError:
                pass
        return data
    except zipfile.error:
        return 'invalid'


def prompt_consent(data):
    table_title = props.Translatable({
        "en": "Number of posts on Instagram",
        "nl": "Aantal posts op Instagram"
    })
    data_frame = pd.DataFrame(data, columns=["Type", "Count"])
    table = props.PropsUIPromptConsentFormTable("zip_content", table_title, data_frame)
    return props.PropsUIPromptConsentForm([table], [])


def donate(key, json_string):
    return CommandSystemDonate(key, json_string)


def exit():
    page = props.PropsUIPageEnd()
    return CommandUIRender(page)
