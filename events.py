import sublime
import sublime_plugin
import os
import time
import re

from . import context
from . import util
from .salesforce.lib.panel import Printer

class SFDCEventListener(sublime_plugin.EventListener):
    def on_new(self, view):
        """
        1. Eveytime when you open a new view, default syntax is Apex
        2. Set Status with current default project
        """
        view.set_syntax_file("Packages/Java/Java.tmLanguage")
        util.display_active_project(view)

    def on_load_async(self, view):
        """ Set Status with current default project
        """

        util.display_active_project(view)

        # Add types settings for build_package_xml command
        if view.file_name() != None:
            cname = os.path.basename(view.file_name())
            if cname and "package.xml" in cname.lower():
                with open(view.file_name(), "rb") as fp:
                    content = fp.read()
                try:
                    types = util.build_package_types(content)
                    view.settings().set("types", types)
                except:
                    pass

    def on_post_save_async(self, view):
        settings = context.get_settings();
        if not view.file_name(): return
        file_name = view.file_name().replace("\\", "/")
        workspace = settings["workspace"].replace("\\", "/")
        if workspace not in file_name: return
        if settings.get('auto_update_on_save'):
            view.run_command('save_to_server')

    def on_activated(self, view):
        """ 
            1. Switch project to which view file is in
            2. Sync sidebar with view file
            3. Set Status with current default project
        """

        settings = context.get_settings()

        file_name = view.file_name()
        if settings["auto_switch_project_on_file_activated"] and file_name:
            project_name = util.get_path_attr(file_name)[0]
            if project_name in settings["projects"].keys():
                util.switch_project(project_name)

        if settings["reveal_file_in_sidebar_on_file_activated"]:
            view.window().run_command("reveal_in_side_bar")

        util.display_active_project(view)

    def on_query_completions(self, view, prefix, locations):
        if not view.match_selector(locations[0], "text.html - source"):
            return []

        location = locations[0]
        pt = locations[0] - len(prefix) - 1
        ch = view.substr(sublime.Region(pt, pt + 1))
        
        # If char is not # or current view is not file, just skip
        if ch != "#" or not view.file_name(): return

        begin = view.full_line(pt).begin()
        matched_region = view.find('(controller="\\w+#"|extensions="\\w+#")', begin)
        if not matched_region: return
        matched_block = view.substr(matched_region).strip()

        # Delete the input #
        view.run_command("left_delete")

        # Get the Class Name
        class_name = view.substr(view.word(pt-1))

        # Get the template type
        if "controller" in matched_block:
            template_name = "Controller"
        elif "extensions" in matched_block:
            template_name = "StandardController Extension"

        # Check whether project of current page is active
        settings = context.get_settings();
        base, name = os.path.split(view.file_name())
        src, meta_type = os.path.split(base)
        default_project = settings["default_project_name"]
        if default_project not in src:
            Printer.get('error').write("Current page is not in active project")
            return

        # Check whether the class is exist
        file_name = os.path.join(src, "classes", class_name+".cls")
        if os.path.exists(file_name): 
            Printer.get('error').write("%s is already exist" % class_name)
            return

        sublime.active_window().run_command("create_component", {
            "template_name": template_name,
            "component_name": class_name,
            "component_type": "ApexClass",
            "markup_or_body": "Body"
        })
