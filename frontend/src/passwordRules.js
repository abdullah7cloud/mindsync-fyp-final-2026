// The password rules shown to the student. They mirror the server's rules (backend app/schemas.py), which are the
// ones that really count; showing them here just saves a round trip.
export function passwordRules(pw) {
  return [
    { ok: pw.length >= 8, text: "At least 8 characters" },
    { ok: /[A-Za-z]/.test(pw), text: "At least one letter" },
    { ok: /\d/.test(pw), text: "At least one number" },
  ];
}
