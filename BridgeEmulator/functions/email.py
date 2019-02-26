import smtplib, logging

def sendEmail(config, triggered_sensor):

    TEXT = "Sensor " + triggered_sensor + " was triggered while the alarm is active"
    # Prepare actual message
    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (config["mail_from"], ", ".join(config["mail_recipients"]), config["mail_subject"], TEXT)
    try:
        server_ssl = smtplib.SMTP_SSL(config["smtp_server"], config["smtp_port"])
        server_ssl.ehlo() # optional, called by login()
        server_ssl.login(config["mail_username"], config["mail_password"])
        server_ssl.sendmail(config["mail_from"], config["mail_recipients"], message)
        server_ssl.close()
        logging.info("successfully sent the mail")

        return True
    except:
        logging.exception("failed to send mail")
        return False
