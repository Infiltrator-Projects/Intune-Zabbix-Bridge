#!/usr/bin/env python3
"""GTK configuration utility for Intune-Zabbix-Bridge.

The GUI intentionally keeps privileged filesystem/service operations out of the
desktop process. Save/Start hands a temporary configuration file to a small
root helper through pkexec, so normal Mint users can configure the bridge
without opening a terminal or editing /etc manually.
"""

from __future__ import annotations

import os
import subprocess
import tempfile

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

DEFAULTS = {
    "AZURE_TENANT_ID": "",
    "AZURE_CLIENT_ID": "",
    "AZURE_CLIENT_SECRET": "",
    "INTUNE_TELEMETRY_SCRIPT_ID": "e00b219b-d616-4164-accc-b1a61725c7a4",
    "ZABBIX_SERVER": "127.0.0.1",
    "ZABBIX_PORT": "10051",
    "ZABBIX_HOST": "Microsoft Intune - Windows Fleet",
    "ZABBIX_SENDER": "zabbix_sender",
    "TIMEZONE": "Australia/Melbourne",
    "MAX_TELEMETRY_AGE_HOURS": "48",
    "TOP_N": "10",
    "HTTP_TIMEOUT_SECONDS": "20",
    "HTTP_RETRIES": "4",
    "LOG_LEVEL": "INFO",
}

REQUIRED = (
    "AZURE_TENANT_ID",
    "AZURE_CLIENT_ID",
    "AZURE_CLIENT_SECRET",
    "INTUNE_TELEMETRY_SCRIPT_ID",
)


class BridgeConfigWindow(Gtk.Window):
    def __init__(self) -> None:
        super().__init__(title="Intune Zabbix Bridge Setup")
        self.set_default_size(680, 560)
        self.set_border_width(18)

        self.entries: dict[str, Gtk.Entry] = {}

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.add(outer)

        title = Gtk.Label()
        title.set_markup("<span size='xx-large' weight='bold'>Intune Zabbix Bridge</span>")
        title.set_xalign(0)
        outer.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(
            label=(
                "Configure the Microsoft Intune connection used by the Zabbix "
                "reboot-telemetry collector. No terminal editing is required."
            )
        )
        subtitle.set_xalign(0)
        subtitle.set_line_wrap(True)
        outer.pack_start(subtitle, False, False, 0)

        creds_frame = Gtk.Frame(label="Microsoft Entra / Intune")
        creds_grid = Gtk.Grid(column_spacing=12, row_spacing=10, margin=12)
        creds_frame.add(creds_grid)
        outer.pack_start(creds_frame, False, False, 0)

        fields = [
            ("AZURE_TENANT_ID", "Tenant ID"),
            ("AZURE_CLIENT_ID", "Client / Application ID"),
            ("AZURE_CLIENT_SECRET", "Client secret"),
            ("INTUNE_TELEMETRY_SCRIPT_ID", "Intune telemetry script ID"),
        ]

        for row, (key, label_text) in enumerate(fields):
            label = Gtk.Label(label=label_text)
            label.set_xalign(0)
            entry = Gtk.Entry()
            entry.set_hexpand(True)
            entry.set_text(DEFAULTS[key])
            if key == "AZURE_CLIENT_SECRET":
                entry.set_visibility(False)
                entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
            creds_grid.attach(label, 0, row, 1, 1)
            creds_grid.attach(entry, 1, row, 1, 1)
            self.entries[key] = entry

        advanced = Gtk.Expander(label="Advanced Zabbix / collector settings")
        advanced_grid = Gtk.Grid(column_spacing=12, row_spacing=10, margin=12)
        advanced.add(advanced_grid)
        outer.pack_start(advanced, False, False, 0)

        advanced_fields = [
            ("ZABBIX_SERVER", "Zabbix server"),
            ("ZABBIX_PORT", "Zabbix port"),
            ("ZABBIX_HOST", "Zabbix host"),
            ("TIMEZONE", "Timezone"),
            ("MAX_TELEMETRY_AGE_HOURS", "Endpoint telemetry max age (hours)"),
            ("TOP_N", "Rows / Top N"),
        ]

        for row, (key, label_text) in enumerate(advanced_fields):
            label = Gtk.Label(label=label_text)
            label.set_xalign(0)
            entry = Gtk.Entry()
            entry.set_hexpand(True)
            entry.set_text(DEFAULTS[key])
            advanced_grid.attach(label, 0, row, 1, 1)
            advanced_grid.attach(entry, 1, row, 1, 1)
            self.entries[key] = entry

        self.status = Gtk.Label(label="Enter the three Entra values, then click Save & Start Collector.")
        self.status.set_xalign(0)
        self.status.set_line_wrap(True)
        outer.pack_start(self.status, False, False, 0)

        buttons = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        buttons.set_layout(Gtk.ButtonBoxStyle.END)

        close = Gtk.Button(label="Close")
        close.connect("clicked", lambda *_: self.close())
        buttons.add(close)

        save = Gtk.Button(label="Save && Start Collector")
        save.get_style_context().add_class("suggested-action")
        save.connect("clicked", self.on_save)
        buttons.add(save)
        self.save_button = save

        outer.pack_end(buttons, False, False, 0)

    def _value(self, key: str) -> str:
        if key in self.entries:
            return self.entries[key].get_text().strip()
        return DEFAULTS[key]

    def on_save(self, _button: Gtk.Button) -> None:
        missing = [key for key in REQUIRED if not self._value(key)]
        if missing:
            self._error("Please fill in Tenant ID, Client ID, Client secret and telemetry script ID.")
            return

        values = dict(DEFAULTS)
        for key in self.entries:
            values[key] = self._value(key)

        # Keep fixed implementation keys out of the visible form while still
        # writing a complete EnvironmentFile.
        values["ZABBIX_SENDER"] = DEFAULTS["ZABBIX_SENDER"]
        values["HTTP_TIMEOUT_SECONDS"] = DEFAULTS["HTTP_TIMEOUT_SECONDS"]
        values["HTTP_RETRIES"] = DEFAULTS["HTTP_RETRIES"]
        values["LOG_LEVEL"] = DEFAULTS["LOG_LEVEL"]

        content = "".join(f'{key}="{value.replace(chr(34), chr(92)+chr(34))}"\n' for key, value in values.items())

        fd, path = tempfile.mkstemp(prefix="intune-zabbix-bridge-", suffix=".env")
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)

            self.save_button.set_sensitive(False)
            self.status.set_text("Saving configuration and starting the collector…")

            completed = subprocess.run(
                [
                    "pkexec",
                    "/usr/lib/intune-zabbix-bridge/config-helper",
                    "install",
                    path,
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )

            if completed.returncode != 0:
                self._error(
                    "Configuration was not applied.\n\n"
                    + (completed.stdout.strip() or "Administrator authorisation was cancelled.")
                )
                return

            message = completed.stdout.strip() or "Configuration saved and collector started."
            self.status.set_text(message)
            self._info(message)

        finally:
            self.save_button.set_sensitive(True)
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass

    def _error(self, message: str) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Intune Zabbix Bridge",
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def _info(self, message: str) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Intune Zabbix Bridge",
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


def main() -> int:
    window = BridgeConfigWindow()
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
