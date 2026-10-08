"""
Email templating and sending utilities for TutorOn India.
Provides responsive, modern HTML email templates for OTP verification and password reset.
Theme: Sunset Coral & Warm Amber (Modern Energetic EdTech)
"""

def get_otp_email_content(user_name: str, otp: str, purpose: str = "reset_password", valid_minutes: int = 15):
    """
    Returns (subject, plain_text_message, html_message)
    purpose: 'reset_password' or 'verify_email'
    """
    user_name = user_name or "User"
    otp_str = str(otp).strip()

    if purpose == "reset_password":
        subject = "Reset your TutorOn India Password - OTP"
        headline = "Password Reset Request"
        instruction = (
            "We received a request to reset your password for your <strong>TutorOn India</strong> account. "
            "Please use the One-Time Password (OTP) below to proceed:"
        )
        plain_text = (
            f"Hello {user_name},\n\n"
            f"We received a request to reset your password for TutorOn India.\n\n"
            f"Your 6-digit OTP is: {otp_str}\n\n"
            f"This OTP is valid for {valid_minutes} minutes only.\n\n"
            f"Security Note: Never share this OTP with anyone. If you didn't request a password reset, you can safely ignore this email.\n\n"
            f"Team TutorOn India"
        )
    else:  # verify_email
        subject = "Verify your TutorOn India Email - OTP"
        headline = "Verify Your Email Address"
        instruction = (
            "Welcome to <strong>TutorOn India</strong>! Thank you for registering. "
            "Please use the One-Time Password (OTP) below to verify your email address and activate your account:"
        )
        plain_text = (
            f"Hello {user_name},\n\n"
            f"Welcome to TutorOn India!\n\n"
            f"Your 6-digit verification OTP is: {otp_str}\n\n"
            f"This OTP is valid for {valid_minutes} minutes only.\n\n"
            f"Team TutorOn India"
        )

    # Build individual digit boxes inside a single table row to guarantee 100% single-line display
    otp_cells = []
    total_digits = len(otp_str)
    for idx, digit in enumerate(otp_str):
        padding_right = "8px" if idx < total_digits - 1 else "0"
        otp_cells.append(
            f'<td align="center" valign="middle" style="padding-right: {padding_right};">'
            f'<div style="width: 44px; height: 50px; line-height: 50px; background: #ffffff; border: 1.5px solid #fdba74; border-radius: 10px; font-size: 26px; font-weight: 800; color: #c2410c; font-family: \'SFMono-Regular\', Consolas, Menlo, Monaco, monospace; text-align: center; box-shadow: 0 2px 4px rgba(234, 88, 12, 0.08);">'
            f'{digit}'
            f'</div>'
            f'</td>'
        )
    otp_row_html = "".join(otp_cells)

    html_message = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="format-detection" content="telephone=no, date=no, address=no, email=no">
  <title>{subject}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #fdfaf7; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; color: #1e293b; -webkit-font-smoothing: antialiased;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #fdfaf7; width: 100%; padding: 40px 15px;">
    <tr>
      <td align="center">
        <!-- Main Card Container -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 540px; background-color: #ffffff; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 35px rgba(234, 88, 12, 0.08); border: 1px solid #fed7aa;">
          
          <!-- Header Banner (Sunset Coral & Warm Amber Gradient) -->
          <tr>
            <td style="background: linear-gradient(135deg, #f43f5e 0%, #ea580c 55%, #f59e0b 100%); padding: 38px 30px; text-align: center;">
              <div style="display: inline-block; background: rgba(255, 255, 255, 0.22); border-radius: 50px; padding: 6px 20px; margin-bottom: 12px; border: 1px solid rgba(255, 255, 255, 0.4);">
                <span style="color: #ffffff; font-size: 13px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase;">
                  TUTORON INDIA
                </span>
              </div>
              <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; text-shadow: 0 1px 3px rgba(0,0,0,0.12);">
                {headline}
              </h1>
            </td>
          </tr>

          <!-- Body Content -->
          <tr>
            <td style="padding: 36px 32px 28px 32px;">
              <p style="margin: 0 0 16px 0; color: #1e293b; font-size: 16px; line-height: 1.5;">
                Hello <strong>{user_name}</strong>,
              </p>
              
              <p style="margin: 0 0 24px 0; color: #475569; font-size: 14.5px; line-height: 1.6;">
                {instruction}
              </p>

              <!-- OTP Box (Warm Peach & Amber Glow) -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 26px 0;">
                <tr>
                  <td align="center" style="background: #fff7ed; border: 2px dashed #fb923c; border-radius: 16px; padding: 26px 18px;">
                    <div style="font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; color: #ea580c; margin-bottom: 14px;">
                      Your One-Time Password (OTP)
                    </div>
                    
                    <!-- Single-line Digit Boxes Table -->
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="margin: 0 auto; border-collapse: separate; white-space: nowrap;">
                      <tr>
                        {otp_row_html}
                      </tr>
                    </table>

                    <div style="display: inline-block; background: #ffedd5; color: #9a3412; font-size: 12px; font-weight: 600; padding: 5px 14px; border-radius: 20px; border: 1px solid #fed7aa; margin-top: 16px;">
                      Valid for {valid_minutes} minutes only
                    </div>
                  </td>
                </tr>
              </table>

              <!-- Security Caution Note -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 24px 0 16px 0;">
                <tr>
                  <td style="background-color: #fef2f2; border-left: 4px solid #f43f5e; border-radius: 8px; padding: 14px 16px;">
                    <p style="margin: 0; color: #991b1b; font-size: 13px; line-height: 1.5;">
                      <strong>Security Note:</strong> Never share this OTP with anyone, including anyone claiming to be from TutorOn India. We will never ask for your OTP.
                    </p>
                  </td>
                </tr>
              </table>

              <p style="margin: 0; color: #64748b; font-size: 13px; line-height: 1.5;">
                If you did not make this request, please ignore this email. Your account remains completely secure.
              </p>
            </td>
          </tr>

          <!-- Subtle Divider -->
          <tr>
            <td style="padding: 0 32px;">
              <hr style="border: 0; border-top: 1px solid #fed7aa; margin: 0; opacity: 0.5;">
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 24px 32px 32px 32px; background-color: #fffaf5; text-align: center;">
              <p style="margin: 0 0 6px 0; color: #475569; font-size: 13.5px; font-weight: 600;">
                Warm regards,<br>
                <span style="color: #ea580c; font-weight: 700;">Team TutorOn India</span>
              </p>
              <p style="margin: 14px 0 0 0; color: #94a3b8; font-size: 11.5px; line-height: 1.5;">
                This is an automated system notification from TutorOn India.<br>
                Please do not reply directly to this email.
              </p>
              <p style="margin: 8px 0 0 0; color: #cbd5e1; font-size: 11px;">
                &copy; 2026 TutorOn India. All rights reserved.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    return subject, plain_text, html_message
