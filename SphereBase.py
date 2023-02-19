#!/usr/bin/env python
# coding=utf-8
#
"""
Generate Laser Cut Vector to Make Sphere Base.
"""

import math
import svgwrite
import os
import sys
from PySide2 import QtWidgets, QtGui
import webbrowser

X, Y = range(2)

class InputDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()

        self.input_vars = {
            "base_size": 0.0,
            "plate_thick": 0.0,
            "sph_height": 0.0,
            "sph_rad": 0.0,
            "plate_span": 0.0,
            "rect_length": 0.0,
            "rect_height": 0.0
        }

        self.initUI()

    def initUI(self):
        layout = QtWidgets.QHBoxLayout()

        input_form = QtWidgets.QFormLayout()
        for key in self.input_vars:
            line_edit = QtWidgets.QLineEdit()
            input_form.addRow(key, line_edit)
            exec(f"self.{key}_le = line_edit")

        submit_btn = QtWidgets.QPushButton("Submit")
        submit_btn.clicked.connect(self.submit)
        input_form.addWidget(submit_btn)

        layout.addLayout(input_form)

        help_label = QtWidgets.QLabel()
        help_pixmap = QtGui.QPixmap("img/spherebase_help.png")
        help_label.setPixmap(help_pixmap)

        layout.addWidget(help_label)

        self.setLayout(layout)

    def submit(self):
        for key in self.input_vars:
            exec(f"self.input_vars[\'{key}\'] = float(self.{key}_le.text())")

        validation = self.validate_input()
        if validation["failed"]:
            QtWidgets.QMessageBox.warning(self, "Warning", validation["message"] + "Please try again.")
            return

        self.accept()
        obj_sphere = SphereBase(dialog.input_vars)
        obj_sphere.draw_vplates()
        obj_sphere.draw_base()
        obj_sphere.dwg_new.save()
        path_base = os.getcwd()
        webbrowser.open("file://" + os.path.join(path_base, "lasercut_spherebase.svg"))

    def validate_input(self):
        has_failed = False
        message = ""
        if self.input_vars["rect_length"] >= self.input_vars["base_size"] / 2:
            has_failed = True
            message += "rect_length must be lower than base_size / 2.\n"
        
        if self.input_vars["rect_height"] >= self.input_vars["sph_height"] + self.input_vars["sph_rad"]:
            has_failed = True
            message += "rect_height must be lower than sph_height + sph_rad.\n"

        if self.input_vars["plate_span"] >= self.input_vars["base_size"] - 2 * self.input_vars["plate_thick"]:
            has_failed = True
            message += "plate_span must be lower than base_size - 2 * plate_thick.\n"
        
        if self.input_vars["plate_thick"] >= self.input_vars["base_size"] / 2:
            has_failed = True
            message += "plate_thick must be lower than base_size / 2.\n"

        return {"failed": has_failed, "message": message}


class SphereBase():
    def __init__(self, input_results):
        self.base_size = input_results["base_size"]
        self.plate_thick = input_results["plate_thick"]
        self.sph_center = {"position": input_results["base_size"] / 2, "height": input_results["sph_height"]}
        self.sph_rad = input_results["sph_rad"]
        self.plate_span = input_results["plate_span"]
        self.ini_rect = {"length": input_results["rect_length"], "height": input_results["rect_height"]}
        self.has_centerplate = False
        self.num_vplate = 0
        self.list_groove = []
        self.dwg_new = svgwrite.Drawing("lasercut_spherebase.svg", size=("400mm", "300mm"), viewBox=("0 0 400 300"))

    def draw_vplates(self):
        org_point = [3, 3]
        arc_center = [org_point[X] + self.sph_center["position"], org_point[Y] + self.sph_center["height"]]
         
        plate_num = math.ceil((self.base_size - self.plate_thick) / (self.plate_span + self.plate_thick))
        is_even = plate_num % 2 == 0
        sect_pos = 0

        if is_even:
            sect_pos = (self.plate_span + self.plate_thick) / 2
        elif self.needs_vplate(self.sph_rad):
            rect_dim = self.update_rect_dimension(self.sph_rad)
            self.draw_vertical_plate(self.sph_rad, rect_dim, arc_center, org_point)
            org_point[Y] += rect_dim["height"] + 3
            arc_center[Y] += rect_dim["height"] + 3
            self.draw_vertical_plate(self.sph_rad, rect_dim, arc_center, org_point)
            org_point[Y] -= rect_dim["height"] + 3
            arc_center[Y] -= rect_dim["height"] + 3
            self.list_groove.append({"position": sect_pos, "depth": rect_dim["length"] / 2})
            sect_pos += self.plate_span + self.plate_thick
            org_point[X] += rect_dim["length"] + 3
            arc_center = [org_point[X] + self.sph_center["position"], org_point[Y] + self.sph_center["height"]]
            self.has_centerplate = True
            self.num_vplate += 1

        rep_num = math.floor(plate_num / 2)
        for i in range(1, rep_num + 1):

            if self.sph_rad < sect_pos:
                sect_rad = 0
            else:
                sect_rad = math.sqrt(self.sph_rad ** 2 - sect_pos ** 2)

            if not self.needs_vplate(sect_rad):
                continue

            rect_dim = self.update_rect_dimension(sect_rad)
            self.draw_vertical_plate(sect_rad, rect_dim, arc_center, org_point)
            for j in range(1, 4):
                org_point[Y] += rect_dim["height"] + 3
                arc_center[Y] += rect_dim["height"] + 3
                self.draw_vertical_plate(sect_rad, rect_dim, arc_center, org_point)
            org_point[Y] -= (rect_dim["height"] + 3) * 3
            arc_center[Y] -= (rect_dim["height"] + 3) * 3
            self.list_groove.append({"position": sect_pos, "depth": rect_dim["length"] / 2})
            sect_pos += self.plate_span + self.plate_thick
            org_point[X] += rect_dim["length"] + 3
            arc_center = [org_point[X] + self.sph_center["position"], org_point[Y] + self.sph_center["height"]]
            self.num_vplate += 1

        self.center_base = (org_point[X] + self.base_size / 2, 3 + self.base_size / 2)

    def needs_vplate(self, sect_rad):
        return (self.sph_center["position"] - self.plate_thick) ** 2 + (self.sph_center["height"] - 3 * self.plate_thick) ** 2 > sect_rad ** 2

    def update_rect_dimension(self, sect_rad):
        newLength = self.ini_rect["length"]
        newHeight = self.ini_rect["height"]
        if (self.sph_center["position"] - self.ini_rect["length"]) ** 2 + (self.sph_center["height"] - 3 * self.plate_thick) ** 2 < sect_rad ** 2:
            newLength = -math.sqrt(sect_rad ** 2 - (self.sph_center["height"] - 3 * self.plate_thick) ** 2) + self.sph_center["position"]

        if (self.sph_center["position"] - self.plate_thick) ** 2 + (self.sph_center["height"] - self.ini_rect["height"]) ** 2 < sect_rad ** 2:
            newHeight = -math.sqrt(sect_rad ** 2 - (self.sph_center["position"] - self.plate_thick) ** 2) + self.sph_center["height"]

        return {"length": newLength, "height": newHeight}

    # draw a vertical plate
    def draw_vertical_plate(self, sect_rad, rect_dim, arc_center, org_point):
        validate1 = (arc_center[Y] - rect_dim["height"] - org_point[Y]) ** 2
        validate2 = (arc_center[X] - rect_dim["length"] - org_point[X]) ** 2
        has_arc = sect_rad ** 2 - validate1 - validate2 > 0
        str_path = "M {0},{1}".format(org_point[X], org_point[Y]) \
                + " L {0},{1}".format(org_point[X], org_point[Y] + rect_dim["height"])
        if has_arc:
            top_length = arc_center[X] - math.sqrt(sect_rad ** 2 - validate1) - org_point[X]
            right_height = arc_center[Y] - math.sqrt(sect_rad ** 2 - validate2) - org_point[Y]
            str_path += " L {0},{1}".format(org_point[X] + top_length, org_point[Y] + rect_dim["height"]) \
                    + " A {0},{0} 0 0,1 {1},{2}".format(sect_rad, org_point[X] + rect_dim["length"], org_point[Y] + right_height)
        else:
            str_path += " L {0},{1}".format(org_point[X] + rect_dim["length"], org_point[Y] + rect_dim["height"])
        
        str_path += " L {0},{1}".format(org_point[X] + rect_dim["length"], org_point[Y] + 2 * self.plate_thick) \
                + " L {0},{1}".format(org_point[X] + rect_dim["length"] / 2, org_point[Y] + 2 * self.plate_thick) \
                + " L {0},{1}".format(org_point[X] + rect_dim["length"] / 2, org_point[Y] + self.plate_thick) \
                + " L {0},{1}".format(org_point[X] + rect_dim["length"], org_point[Y] + self.plate_thick) \
                + " L {0},{1}".format(org_point[X] + rect_dim["length"], org_point[Y]) \
                + " L {0},{1}".format(org_point[X], org_point[Y])

        path_add = self.dwg_new.path(d=str_path, fill="none", style="stroke:#000000;stroke-width:0.3")
        self.dwg_new.add(path_add)
        return path_add

    def draw_base(self):
        if self.has_centerplate:
            groove_total = 2 * self.num_vplate - 1
        else:
            groove_total = 2 * self.num_vplate
        
        list_groove_lower = []
        list_groove_upper = []
        for i in range(0, groove_total):
            list_groove_lower.append({})
            list_groove_upper.append({})

        for i in range(0, self.num_vplate):
            num_former = self.num_vplate - i - 1
            if self.has_centerplate:
                num_latter = self.num_vplate + i - 1
            else:
                num_latter = self.num_vplate + i
            list_groove_lower[num_latter]["position"] = self.center_base[X] - self.list_groove[i]["position"]
            list_groove_lower[num_latter]["depth"] = self.list_groove[i]["depth"]
            list_groove_upper[num_latter]["position"] = self.center_base[X] + self.list_groove[i]["position"]
            list_groove_upper[num_latter]["depth"] = self.list_groove[i]["depth"]
            list_groove_lower[num_former]["position"] = self.center_base[X] + self.list_groove[i]["position"]
            list_groove_lower[num_former]["depth"] = self.list_groove[i]["depth"]
            list_groove_upper[num_former]["position"] = self.center_base[X] - self.list_groove[i]["position"]
            list_groove_upper[num_former]["depth"] = self.list_groove[i]["depth"]

        self.str_base_path = ""
        self.str_base_path += "M {0},{1}".format(self.center_base[X] + self.base_size / 2, self.center_base[Y] + self.base_size / 2)
        for groove in list_groove_lower:
            self.add_groove_points(groove, -1)

        self.str_base_path += " L {0},{1}".format(self.center_base[X] - self.base_size / 2, self.center_base[Y] + self.base_size / 2)
        self.str_base_path += " L {0},{1}".format(self.center_base[X] - self.base_size / 2, self.center_base[Y] - self.base_size / 2)
        for groove in list_groove_upper:
            self.add_groove_points(groove, 1)

        self.str_base_path += " L {0},{1}".format(self.center_base[X] + self.base_size / 2, self.center_base[Y] - self.base_size / 2)
        self.str_base_path += " L {0},{1}".format(self.center_base[X] + self.base_size / 2, self.center_base[Y] + self.base_size / 2)
        path_add = self.dwg_new.path(d=self.str_base_path, fill="none", style="stroke:#000000;stroke-width:0.3")
        self.dwg_new.add(path_add)

        if self.sph_rad > self.sph_center["height"] - self.plate_thick * 1.5:
            rad_circle = math.sqrt(self.sph_rad ** 2 - (self.sph_center["height"] - self.plate_thick * 1.5) ** 2)
            circle_add = self.dwg_new.circle(center=self.center_base, r=rad_circle, fill="none", style="stroke:#FF0000;stroke-width:0.3")
            self.dwg_new.add(circle_add)
        return path_add
    
    def add_groove_points(self, groove, direction):
        val_y = self.center_base[Y] - direction * self.base_size / 2
        self.str_base_path += " L {0},{1}".format(groove["position"] - direction * self.plate_thick / 2, val_y)
        self.str_base_path += " L {0},{1}".format(groove["position"] - direction * self.plate_thick / 2, val_y + direction * groove["depth"])
        self.str_base_path += " L {0},{1}".format(groove["position"] + direction * self.plate_thick / 2, val_y + direction * groove["depth"])
        self.str_base_path += " L {0},{1}".format(groove["position"] + direction * self.plate_thick / 2, val_y)
        return


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    dialog = InputDialog()
    dialog.show()
    sys.exit(app.exec_())