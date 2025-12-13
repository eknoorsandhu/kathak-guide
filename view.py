"""screen stuff - no camera or file saving in here"""
import pygame

from model import COUNT_IN, STATUS_LABELS, timing_text


class View:
    def __init__(self):
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((1000, 740))
        pygame.display.set_caption("Kathak Practice Guide")
        self.font = pygame.font.Font(None, 26)
        self.heading = pygame.font.Font(None, 38)
        self.buttons = {}

    def text(self, text, x, y, width=940, heading=False):
        font = self.heading if heading else self.font
        # pygame won't wrap the text for us
        for paragraph in str(text).split("\n"):
            line = ""
            for word in paragraph.split():
                try_line = f"{line} {word}".strip()
                if line and font.size(try_line)[0] > width:
                    self.screen.blit(font.render(line, True, (230, 235, 240)), (x, y))
                    y += font.get_linesize()
                    line = word
                else:
                    line = try_line
                # filenames can be one long word so those need splitting too
                while font.size(line)[0] > width:
                    cut = len(line)
                    while font.size(line[:cut])[0] > width:
                        cut -= 1
                    self.screen.blit(font.render(line[:cut], True, (230, 235, 240)), (x, y))
                    y += font.get_linesize()
                    line = line[cut:]
            self.screen.blit(font.render(line, True, (230, 235, 240)), (x, y))
            y += font.get_linesize()
        return y

    def button(self, action, label, x, y, width=180, enabled=True):
        rect = pygame.Rect(x, y, width, 42)
        pygame.draw.rect(self.screen, (47, 95, 114) if enabled else (49, 53, 60), rect, border_radius=5)
        image = self.font.render(label, True, (245, 245, 245) if enabled else (145, 150, 155))
        self.screen.blit(image, image.get_rect(center=rect.center))
        if enabled:
            self.buttons[action] = rect

    def frame(self, frame, box, missing="Waiting for a camera frame..."):
        rect = pygame.Rect(box)
        pygame.draw.rect(self.screen, (10, 13, 17), rect)
        if frame is None:
            self.text(missing, rect.x + 16, rect.y + 16, rect.width - 32)
            return
        height, width = frame.shape[:2]
        image = pygame.image.frombuffer(frame.data, (width, height), "BGR")
        scale = min(rect.width / width, rect.height / height)
        image = pygame.transform.smoothscale(image, (max(1, int(width * scale)), max(1, int(height * scale))))
        self.screen.blit(image, image.get_rect(center=rect.center))  # Don't mirror this or feet get confusing.

    def cue(self, app):
        drill = app.drill
        # count in first, no stepping yet
        beat = int((app.elapsed - app.count_in_start) * drill["bpm"] / 60)
        if beat < COUNT_IN:
            return f"High count-in click {beat + 1} / {COUNT_IN} - wait before stepping"
        contact = beat - COUNT_IN
        if contact >= drill["contacts"]:
            return "Sequence complete - saving your recording."
        foot = drill["first_foot"] if contact % 2 == 0 else ("right" if drill["first_foot"] == "left" else "left")
        return f"Step {contact + 1} / {drill['contacts']}: your {foot.upper()} foot"

    def draw(self, app):
        # clear these or a click might hit a button from the previous screen
        self.buttons = {}
        self.screen.fill((23, 29, 37))
        titles = {"home": "Kathak Practice Guide", "preview": "Check your camera", "recording": "Follow the beat",
                  "processing": "Preparing your saved review", "results": "Timing review", "history": "Saved reviews",
                  "watch": "Source recording replay"}
        self.text(titles[app.page], 30, 25, heading=True)
        if app.page == "home":
            self.text("1. Keep the camera still, show your whole body and feet, and stay in one spot.\n"
                      f"2. Hear {COUNT_IN} high count-in clicks, then alternate one step per beat.\n"
                      "3. Recording stops automatically; check your steps and replay the recording.", 30, 88)
            self.text("Left / right always means YOUR foot, not the side of the screen.", 30, 185)
            self.text("60 beats per minute means one beat each second. Higher numbers are faster.", 30, 213)
            controls = [("Beat speed (per minute)", f"{app.bpm:g}", "bpm_down", "bpm_up"),
                        ("Total steps", str(app.contacts), "contacts_down", "contacts_up"),
                        ("Camera index", str(app.camera_index), "camera_down", "camera_up")]
            for index, (label, value, down, up) in enumerate(controls):
                y = 245 + index * 67
                self.text(f"{label}: {value}", 40, y + 10, 370)
                self.button(down, "-", 440, y, 90)
                self.button(up, "+", 550, y, 90)
            self.button("foot", f"First foot: {app.first_foot}", 40, 453, 290)
            step_seconds = app.contacts * 60 / app.bpm
            count_in_seconds = COUNT_IN * 60 / app.bpm
            total_seconds = step_seconds + count_in_seconds
            self.text(f"Total duration: {total_seconds:.1f} seconds\n"
                      f"{step_seconds:.1f}s stepping + {count_in_seconds:.1f}s count-in",
                      40, 515)
            self.text("Recordings and feedback are saved locally.", 40, 570)
            self.button("preview", "Open camera", 40, 610, 250)
            self.button("history", "Saved reviews", 315, 610, 250)
        elif app.page in ("preview", "recording", "watch"):
            self.frame(app.frame, (30, 88, 940, 474))
            if app.page == "preview":
                self.text(f"Unmirrored. Keep camera still, feet visible, and stay in one spot. Wait for {COUNT_IN} count-in clicks.", 30, 574)
                self.button("record", "Start practice", 30, 617, 250)
                self.button("back", "Back", 305, 617)
            elif app.page == "recording":
                self.text(self.cue(app), 30, 574)
                self.text(f"Recorded {app.elapsed:.1f} seconds", 30, 625)
                self.button("cancel", "Cancel recording", 720, 617, 250)
            else:
                self.text("Your recording with the practice clicks. Watch how your step lines up with the beat.", 30, 574)
                self.button("back", "Back to review", 30, 617, 250)
        elif app.page == "processing":
            self.text("Recording is complete. Checking how your steps line up with the beat.\n"
                      "Your review will open automatically; the recording stays saved.", 30, 105)
            self.text(app.progress, 30, 235)
        elif app.page == "results":
            report = app.report
            counts = report["counts"]
            self.text(f"On beat: {counts['on_time']}  |  Check timing: {counts['early'] + counts['late']}  |  "
                      f"Couldn't assess: {counts['not_detected'] + counts['wrong_foot']}", 30, 86)
            self.text(f"{counts['expected']} practice steps. Camera estimates can be wrong; replay to check.", 30, 125)
            events = app.review_steps
            self.frame(app.frame, (30, 230, 540, 365), "No saved picture for this step. Try replaying it.")
            if events:
                event = events[app.event_index]
                self.text(f"Step {event['beat']} / {counts['expected']} - {event['expected_foot']} foot", 595, 230, 375)
                y = self.text(STATUS_LABELS[event["status"]], 595, 275, 375, heading=True)
                y = self.text(timing_text(event), 595, y + 20, 375)
                self.text("Replay this step to see it with the practice clicks.", 595, y + 20, 375)
            else:
                self.text("No practice steps to review.", 595, 230, 375)
            self.button("event_prev", "Previous step", 30, 617, 180, bool(events) and app.event_index > 0)
            self.button("event_next", "Next step", 225, 617, 180, bool(events) and app.event_index < len(events) - 1)
            self.button("watch", "Replay step", 420, 617, 180, bool(events))
            self.button("history", "Saved reviews", 615, 617, 180)
            self.button("back", "Home", 810, 617, 160)
        elif app.page == "history":
            count = len(app.history)
            # Eight runs fit on the screen; the selected one decides which page we're on.
            start = app.history_index // 8 * 8
            self.text(f"{count} saved reviews | Page {start // 8 + 1} / {max(1, (count + 7) // 8)}", 30, 88)
            for index in range(start, min(start + 8, count)):
                y = 140 + (index - start) * 54
                if index == app.history_index:
                    pygame.draw.rect(self.screen, (47, 95, 114), (30, y - 4, 940, 52), border_radius=5)
                self.text(f"{index + 1}. {app.history[index].name}", 40, y, 910)
            if not count:
                self.text("No completed reviews yet. Start a camera practice to save your first run.", 30, 155)
            self.button("history_prev", "Previous run", 30, 617, 210, count > 0 and app.history_index > 0)
            self.button("history_next", "Next run", 255, 617, 210, count > 0 and app.history_index < count - 1)
            self.button("history_open", "Open selected review", 480, 617, 265, count > 0)
            self.button("back", "Home", 770, 617, 200)
        pygame.draw.rect(self.screen, (32, 39, 48), (0, 670, 1000, 70))
        self.text(app.message, 30, 677)

    def action(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for name, rect in self.buttons.items():
                if rect.collidepoint(event.pos):
                    return name
        return None
