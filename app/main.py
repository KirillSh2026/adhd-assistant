from datetime import datetime
import json
import sys

def add_note(note_type, text, created_note):
    with open("data/notes.json", "r", encoding="utf-8") as f:
        notes = json.load(f)

        notes.append({"type": note_type, "text": text, "datetime": created_note})

        with open("data/notes.json", "w", encoding="utf-8") as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)

def main():

    with open("data/notes.json", "r", encoding="utf-8") as f:
        notes = json.load(f)
    
    note_type = "".join(sys.argv[1])
    text = " ".join(sys.argv[2:])
    created_note = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    filtered_notes = [note for note in notes if note.get('text', '').strip()]
            
    if note_type == "list":
        if text == "task":
            for i, note in enumerate(filtered_notes, 1):
                if note.get('type', '').strip() == "task":
                    if note.get('datetime', ''):
                        print(f"{i}. ({note.get('datetime', '')}) [{note.get('type', '')}]: {note.get('text', '')}")
                    else:
                        print(f"{i}. [{note.get('type', '')}]: {note.get('text', '')}")
        if text == "note":
            for i, note in enumerate(filtered_notes, 1):
                if note.get('type', '').strip() == "note":
                    if  note.get('datetime', ''):
                        print(f"{i}. ({note.get('datetime', '')}) [{note.get('type', '')}]: {note.get('text', '')}")
                    else:
                        print(f"{i}. [{note.get('type', '')}]: {note.get('text', '')}")
        if text == "idea":
            for i, note in enumerate(filtered_notes, 1):
                if note.get('type', '').strip() == "idea":
                    if note.get('datetime', ''):
                        print(f"{i}. ({note.get('datetime', '')}) [{note.get('type', '')}]: {note.get('text', '')}")
                    else:
                        print(f"{i}. [{note.get('type', '')}]: {note.get('text', '')}")
        if text == "all" or text == "":
            for i, note in enumerate(filtered_notes, 1):
                if note.get('datetime', ''):
                    print(f"{i}. ({note.get('datetime', '')}) [{note.get('type', '')}]: {note.get('text', '')}")
                else:
                    print(f"{i}. [{note.get('type', '')}]: {note.get('text', '')}")
    elif note_type == "clear":
        notes = []
        with open("data/notes.json", "w", encoding="utf-8") as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)
    elif text:
        add_note(note_type=note_type, text=text, created_note=created_note)

if __name__ == "__main__":
    main()
