"""
Tests for choosing which sections a task card shows: defaults in Settings, and each
task's own changes from the ☰ Sections menu. Offscreen, temporary data directory.
"""
import logging
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

logger = logging.getLogger("test_task_sections")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def make_task(**fields):
    from models.task import Task
    task = Task(title=fields.pop("title", "A task"), category="Bug")
    for name, value in fields.items():
        setattr(task, name, value)
    return task


# ---------------------------------------------------------------- the rules

def test_everything_is_shown_by_default(app):
    from utils import task_sections
    assert all(task_sections.shown_sections(make_task()).values())


def test_defaults_apply_to_tasks_that_havent_changed_them(app):
    from utils import task_sections
    task = make_task()
    task_sections.set_default("dependencies", False)
    assert not task_sections.is_shown(task, "dependencies")
    task_sections.set_default("dependencies", True)
    assert task_sections.is_shown(task, "dependencies")


def test_a_task_keeps_only_its_differences(app):
    from utils import task_sections
    task = make_task()
    task_sections.set_shown(task, "attachments", False)
    assert task.visible_sections == {"attachments": False}
    task_sections.set_shown(task, "attachments", True)  # same as the default: follow it again
    assert task.visible_sections == {}


def test_a_changed_task_keeps_its_choice_when_defaults_change(app):
    from utils import task_sections
    task = make_task()
    task_sections.set_shown(task, "checklist", False)
    task_sections.set_default("checklist", True)
    assert not task_sections.is_shown(task, "checklist")
    assert task_sections.is_shown(make_task(), "checklist")


def test_reset_and_make_defaults(app):
    from utils import task_sections
    task = make_task()
    task_sections.set_shown(task, "activity", False)
    assert task_sections.is_customized(task)
    task_sections.make_defaults(task)
    assert task.visible_sections == {} and not task_sections.defaults()["activity"]
    assert not task_sections.is_shown(make_task(), "activity")  # new tasks follow

    task_sections.set_shown(task, "activity", True)
    task_sections.reset(task)
    assert not task_sections.is_shown(task, "activity")


def test_tasks_saved_the_old_way_still_load(app):
    """Before defaults, the settings page stored every section; those choices still apply"""
    from utils import task_sections
    task = make_task(visible_sections={key: key != "details" for key in task_sections.KEYS})
    assert not task_sections.is_shown(task, "details")
    assert task_sections.is_shown(task, "description")
    assert task_sections.is_customized(task)


# ---------------------------------------------------------------- in the task card

def menu_actions(menu):
    return {action.text(): action for action in menu.actions()}


def test_the_sections_menu_adds_and_removes_sections(app):
    from ui.task_files.task_card_expanded import TaskCardExpanded
    from utils.tasks_io import load_tasks_from_json, save_task_to_json
    task = make_task()
    save_task_to_json(task, logger)
    card = TaskCardExpanded(logger=logger, task=load_tasks_from_json(logger, force_reload=True)[task.id])
    card.show()
    assert card.sections_btn.text() == "☰ Sections"

    actions = menu_actions(card.buildSectionsMenu())
    assert actions["Attachments"].isChecked()
    assert not actions["Reset to the defaults"].isEnabled()  # nothing changed yet
    actions["Attachments"].trigger()  # untick: remove it from this card
    assert not card.attachments_section.isVisible()
    saved = load_tasks_from_json(logger, force_reload=True)[task.id]
    assert saved.visible_sections == {"attachments": False}  # saved straight away

    actions = menu_actions(card.buildSectionsMenu())
    assert not actions["Attachments"].isChecked()
    actions["Reset to the defaults"].trigger()
    assert card.attachments_section.isVisible()
    card.close()


def test_make_these_the_defaults_from_a_card(app):
    from ui.task_files.task_card_expanded import TaskCardExpanded
    from utils import task_sections
    card = TaskCardExpanded(logger=logger, task=make_task())
    card.show()
    menu_actions(card.buildSectionsMenu())["Dependencies"].trigger()
    menu_actions(card.buildSectionsMenu())["Make these the defaults"].trigger()
    assert not task_sections.defaults()["dependencies"]

    other = TaskCardExpanded(logger=logger, task=make_task(title="Another"))
    other.show()
    assert not other.dependencies_section.isVisible()
    card.close(), other.close()


def test_settings_switches_set_the_defaults(app):
    from ui.settings_screen import SettingsScreen
    from ui.task_files.task_card_expanded import TaskCardExpanded
    settings = SettingsScreen(logger=logger)
    settings.section_checkboxes["checklist"].setChecked(False)

    card = TaskCardExpanded(logger=logger, task=make_task())
    card.show()
    assert not card.checklist_section.isVisible()
    assert card.description_section_widget.isVisible()
    card.close()
