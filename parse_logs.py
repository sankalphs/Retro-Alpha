import json
with open("space_logs.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()
out_lines = []
for line in lines:
    if line.startswith("data: "):
        try:
            d = json.loads(line[6:])["data"]
            out_lines.append(d)
        except Exception:
            out_lines.append(line.strip())
with open("space_logs_clean.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines))
print("Total cleaned lines:", len(out_lines))
