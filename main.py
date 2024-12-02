print("""

Welcome to SnapSketch Organizer

""")
import mysql.connector

def create_database():
    """
    Create a database and necessary tables.
    """
    try:
        user = input("Enter user: ")
        password = input("Enter SQL password: ")

        # Connect to MySQL server
        db = mysql.connector.connect(
            host="localhost",
            user=user,
            password=password,
        )

        cursor = db.cursor()

        # Create the project database
        cursor.execute("CREATE DATABASE IF NOT EXISTS project")
        db.commit()

        # Switch to the project database
        cursor.execute("USE project")
        db.commit()

        # Create categories table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id INT AUTO_INCREMENT PRIMARY KEY,
            category_name CHAR(50) NOT NULL,
            parent_category_id INT,
            category_path TEXT,
            h_order INT NOT NULL,
            UNIQUE (category_name, parent_category_id)
        );
        """)
        db.commit()


        
        # Create screenshots table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS screenshots (
            screenshot_id INT AUTO_INCREMENT PRIMARY KEY,
            screenshot_name varchar(50) NOT NULL,
            annotation TEXT,
            category_id INT,
            FOREIGN KEY (category_id) REFERENCES categories(category_id),
            UNIQUE (category_id, screenshot_name)
        );
        """)
        db.commit()

        print("Database and tables created successfully!")

    except mysql.connector.Error as err:
        print(f"Error: {err}")

    finally:
        if 'db' in locals() and db.is_connected():
            cursor.close()
            db.close()
config=input("using first time? y/n")
if config=='y':
    create_database()

import pyautogui
import cv2
import numpy as np
import keyboard
import threading
import time
import os

"""
sql login
"""
user=input("enter user: ")
password=input("enter sql password: ")
db=mysql.connector.connect(
    host="localhost",
    user=user,
    password=password,
    database="project"
)
cursor = db.cursor()

"""
Categories:

category_name: Name of the category/folder where screenshots are stored.
category_id: Unique identifier for each category.

"""

class CategoryManager:
    @staticmethod
    def create_category(category_name):
        
        # Create directory for the category
        os.mkdir(category_name)
        path = category_name

        # Insert category into the database
        insert_category_query = "INSERT INTO Categories (category_name,category_path,h_order) VALUES (%s,%s,%s)"
        category_data = (category_name,path,1)
        cursor.execute(insert_category_query, category_data)
        
        category_id = cursor.lastrowid
        db.commit()

        return category_id, path

    @staticmethod
    def create_subcategory(subcategory_name, parent_category_id):
        
        # Retrieve parent category's path
        parent_category_path_query = "SELECT category_path,h_order FROM Categories WHERE category_id = %s"
        cursor.execute(parent_category_path_query, (parent_category_id,))
        parent_category_path,parent_h_order = cursor.fetchone()
        db.commit()

        # Create directory for the subcategory within its parent category directory
        path = os.path.join(parent_category_path, subcategory_name)
        os.mkdir(path)
  
        # Insert subcategory into the database
        insert_subcategory_query = "INSERT INTO Categories (category_name, parent_category_id,category_path,h_order) VALUES (%s, %s,%s,%s)"
        subcategory_data = (subcategory_name, parent_category_id,path,parent_h_order+1)
        cursor.execute(insert_subcategory_query, subcategory_data)
        subcategory_id = cursor.lastrowid
        db.commit()

        return subcategory_id, path

    def get_all_senior_categories(self):                                     # want with heirarchy # also create get all children category function
        # Fetch all category names from the database
        query = "SELECT category_name,category_id FROM Categories where h_order=%s"
        cursor.execute(query,(1,))
        categories = cursor.fetchall()

        # Extract category names from the result set and return as a list
        category = [category for category in categories]

        return category
    
    def get_all_children_categories(self,parent_category_id):
        query = "select category_name,category_id from categories where parent_category_id=%s"
        cursor.execute(query,(parent_category_id,))
        categories = cursor.fetchall()

        category = [category for category in categories]
        
        return category
        
        

class Category:
    def __init__(self, name,is_sub,parent_category=None):
        self.name = name

        if not is_sub:
            self.id,self.path = CategoryManager.create_category(name)

    def create_subcategory(self, subcategory_name):
        subc=Category(subcategory_name,True)
        subc.id,subc.path = CategoryManager.create_subcategory(subcategory_name, self.id)
        return subc #return the category object created

    # Other methods for managing primary categories

"""
screenshot
screenshot_name: Name or title of the screenshot.
screenshot_id: Unique identifier for each screenshot.
category_id: Foreign key linking the screenshot to its respective category.
annotation: Additional notes or annotations attached to the screenshot.
"""
class ScreenShot:
    def __init__(self, name, category_id, annotation): # category or subcategory id
        self.name = name
        self.category_id = category_id
        
        category_query = "SELECT category_path FROM Categories WHERE category_id = %s"
        cursor.execute(category_query, (self.category_id,))
        self.path= cursor.fetchone()[0]   
        
        self.annotation = annotation
        insert_screenshot_query="INSERT INTO screenshots(screenshot_name,category_id,annotation) VALUES (%s,%s,%s)"
        screenshot_data=(self.name,self.category_id,self.annotation)
        cursor.execute(insert_screenshot_query,screenshot_data)
        self.id=cursor.lastrowid
        db.commit()

    def capture_and_save(self):
        image = pyautogui.screenshot()
        image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        screenshot_path = os.path.join(self.path, f"{self.name}.png")
        cv2.imwrite(screenshot_path, image)

        return screenshot_path


class ScreenshotHandler:
    def __init__(self, key='.', duration=float('inf')): 
        self.key = key
        self.duration = duration
        self.running = False
        self.screenshot_count = 1  # Initialize the screenshot count

    def capture_by_key(self, base_name, category_id, annotation):
        while self.running:
            if keyboard.is_pressed(self.key):
                name = f"{base_name}_{self.screenshot_count}"
                screenshot = ScreenShot(name, category_id, annotation)
                screenshot.capture_and_save()
                self.screenshot_count += 1
                time.sleep(1)  


    def activate(self, base_name, category_id, annotation):
        self.running = True
        thread = threading.Thread(target=self.capture_by_key, args=(base_name, category_id, annotation))
        thread.start()

        if self.duration != float('inf'):
            timer = threading.Timer(self.duration, self.stop_capture)
            timer.start()

    def stop_capture(self):
        self.running = False

    def change_key(self, new_key):
        self.key = new_key

#*************************************************************************************************************# under progress

"""
Organizer Class:
Categorization Functions:

create_category(folder_name): Method to create a new category or folder for organizing screenshots.
move_to_category(screenshot_name, category): Function to move a screenshot to a specified category.
Annotation Functions:

add_annotation(screenshot_name, annotation): Method to add notes or annotations to a specific screenshot.
"""

class Organizer:
    def __init__(self):
        pass
    def get_screenshot_id_by_name(self,screenshot_name, category_id):
        # Implement logic to retrieve the screenshot ID based on its name
        query = "SELECT screenshot_id FROM Screenshots WHERE screenshot_name = %s AND category_id = %s"
        cursor.execute(query, (screenshot_name, category_id))
        result = cursor.fetchone()

        return result[0] if result else None
    def get_category_name(self,category_id):
        query="SELECT category_name FROM categories WHERE category_id= %s"
        cursor.execute(query,(category_id,))
        result=cursor.fetchone()
        if result:return result[0]

    def get_category_path(self,category_id):
        query="SELECT category_path FROM categories WHERE category_id= %s"
        cursor.execute(query,(category_id,))
        result=cursor.fetchone()
        if result:return result[0]

    def move_to_category(self, screenshot_id, new_category_id):


        # Retrieve screenshot information to get the file path
        screenshot_query = "SELECT * FROM Screenshots WHERE screenshot_id = %s"
        cursor.execute(screenshot_query, (screenshot_id,))
        screenshot_info = cursor.fetchone()
        screenshot_name = screenshot_info[1]
        old_category_id = screenshot_info[2]
        
        # Update database entry for the screenshot with the new category ID
        update_query = "UPDATE Screenshots SET category_id = %s WHERE screenshot_id = %s"
        update_data = (new_category_id, screenshot_id)
        cursor.execute(update_query, update_data)
        db.commit()
      
        # File paths for old and new categories
    
        old_category_path = self.get_category_path(old_category_id)
        new_category_path = self.get_category_path(new_category_id)
        
        screenshot_path = os.path.join(old_category_path, screenshot_name + ".png")
        new_screenshot_path = os.path.join(new_category_path, screenshot_name + ".png")
        
        os.rename(screenshot_path, new_screenshot_path)
                
        # Logic to move a screenshot to a different category or subcategory
        # You'll need to update the database entry for the screenshot with the new category and subcategory IDs

    def add_annotation(self, screenshot_id, annotation):
        # Logic to add annotations to a specific screenshot
        # Update the annotation field in the database for the specified screenshot
        update_query = "UPDATE Screenshots SET annotation = %s WHERE screenshot_id = %s"
        update_data = (annotation, screenshot_id)
        cursor.execute(update_query, update_data)
        db.commit()

        # Logic to delete a specific screenshot from the system
        # Delete the corresponding database entry and file from the storage
    def delete_screenshot(self, screenshot_id):
    # Retrieve the file path for the screenshot
        file_query = "SELECT category_id, screenshot_name FROM Screenshots WHERE screenshot_id = %s"
        cursor.execute(file_query, (screenshot_id,))
        result = cursor.fetchone()
        category_id, screenshot_name = result

    # Retrieve the category path for the file
        category_path_query = "SELECT category_path FROM Categories WHERE category_id = %s"
        cursor.execute(category_path_query, (category_id,))
        category_path = cursor.fetchone()[0]

    # Create the file path and delete the file
        file_path = os.path.join(category_path, f"{screenshot_name}.png")
        if os.path.exists(file_path):
            os.remove(file_path)

    # Delete the database entry for the screenshot
        delete_query = "DELETE FROM Screenshots WHERE screenshot_id = %s"
        cursor.execute(delete_query, (screenshot_id,))
        db.commit()


    def get_screenshots_in_category(self, category_id):
        # Retrieve screenshots from a particular category
        screenshot_query = "SELECT screenshot_name FROM Screenshots WHERE category_id = %s"
        cursor.execute(screenshot_query, (category_id,))
        screenshots = cursor.fetchall()

        # Return a list of screenshots (can be processed further)
        return screenshots

    # Other relevant methods to manage and retrieve screenshots


#**********************************************************************************************************# gui part
"""
initial screen should contain three buttons
and it will show the current directory and the subcategory and also give the menu to change (it will be in menu not to be typed)
idea about the display
cat:[menu of super categories]
sub cat:[]
sub sub cat:
<buttons>
sub category and sub sub category button should appear after chosing the category and sub category respectively, and its endless
1.to take screenshot  ( a camera icon): will save the screenshot in the chosen directory
2.to veiw screen short : accompanied by a menu containing screenshots
3.edit screenshot : accompanied by a menu containing screenshots open the paint app
4.to create category
and veiwing option should give the paint widget at end
button 
"""
import os
import tkinter as tk
from tkinter import ttk, colorchooser, filedialog,simpledialog
from PIL import Image, ImageDraw, ImageTk


class PaintApp:
    def __init__(self, root, image_path=None):
        self.root = root
        self.root.title("SnapSketch Organizer")
        # Set a fixed size for the canvas
        canvas_width = 800
        canvas_height = 400

        # Create a vertical scrollbar
        self.scrollbar_y = tk.Scrollbar(root, orient=tk.VERTICAL)
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        # Create a horizontal scrollbar
        self.scrollbar_x = tk.Scrollbar(root, orient=tk.HORIZONTAL)
        self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Create a frame to hold the canvas and buttons
        self.scroll_frame = tk.Frame(root)
        self.scroll_frame.pack(fill=tk.BOTH, expand=True)

        # Create the canvas with both vertical and horizontal scrollbars
        self.canvas = tk.Canvas(self.scroll_frame, bg="white", yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure the scrollbars to control the canvas
        self.scrollbar_y.config(command=self.canvas.yview)
        self.scrollbar_x.config(command=self.canvas.xview)

        # Set the fixed size for the canvas
        self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height), width=canvas_width, height=canvas_height)

        # Stylish buttons using ttk
        style = ttk.Style()
        style.configure('TButton', font=('calibri', 9, 'bold', 'italic'), 
                        borderwidth='2', relief="flat", background="lightgray")

        self.color_button = ttk.Button(root, text="Choose Color", command=self.choose_color, style='TButton')
        self.color_button.pack(pady=5)

        self.clear_button = ttk.Button(root, text="Clear Canvas", command=self.clear_canvas, style='TButton')
        self.clear_button.pack(pady=5)

        self.save_button = ttk.Button(root, text="Save Image", command=self.save_canvas, style='TButton')
        self.save_button.pack(pady=5)

        self.undo_button = ttk.Button(root, text="Undo", command=self.undo, style='TButton')
        self.undo_button.pack(pady=5)

        self.tool_var = tk.StringVar()
        self.tool_var.set("line")

        self.tool_frame = tk.Frame(root)
        self.tool_frame.pack(pady=5)

        self.tool_label = tk.Label(self.tool_frame, text="Drawing Tool:")
        self.tool_label.pack(side=tk.LEFT)

        self.tool_menu = tk.OptionMenu(self.tool_frame, self.tool_var, "line", "pencil")
        self.tool_menu.pack(side=tk.LEFT)

        self.drawn_items = []
        self.color = "black"
        self.old_x, self.old_y = None, None
        self.mouse_pressed = False  # To track whether the mouse button is pressed
        self.current_tool = "line"

        self.image_path = image_path
        if image_path:
            self.load_image(image_path)

        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<ButtonRelease-1>", self.release)
        self.canvas.bind("<ButtonPress-1>", self.press)

    def choose_color(self):
        color = colorchooser.askcolor()[1]
        if color:
            self.color = color

    def clear_canvas(self):
        self.canvas.delete("all")
        self.drawn_items = []

    def save_canvas(self):
        if self.image_path:
            img = Image.open(self.image_path)
            img_draw = ImageDraw.Draw(img)

            for item in self.drawn_items:
                coords = self.canvas.coords(item)
                color = self.canvas.itemcget(item, "fill")
                width = self.canvas.itemcget(item, "width")
                tags = self.canvas.gettags(item)

                if "line" in tags:
                    img_draw.line(coords, fill=color, width=int(float(width)))
                elif "pencil" in tags:
                    coords = [int(coord) for coord in coords]
                    img_draw.ellipse(coords, fill=color, outline=color)

            img.save(self.image_path, format="png")

    def paint(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self.mouse_pressed and self.old_x is not None and self.old_y is not None:
            if self.current_tool == "line":
                item = self.canvas.create_line(
                    self.old_x, self.old_y, x, y, width=2,
                    fill=self.color, capstyle=tk.ROUND, smooth=tk.TRUE, tags="line"
                )
            elif self.current_tool == "pencil":
                item = self.canvas.create_oval(
                    x - 2, y - 2, x + 2, y + 2,
                    fill=self.color, outline=self.color, tags="pencil"
                )
            self.drawn_items.append(item)

        self.old_x, self.old_y = x, y

    def release(self, event):
        self.mouse_pressed = False
        self.old_x, self.old_y = None, None

    def press(self, event):
        self.mouse_pressed = True

    def undo(self):
        if self.drawn_items:
            item = self.drawn_items.pop()
            self.canvas.delete(item)

    def load_image(self, image_path):
        if image_path:
            img = Image.open(image_path)
            canvas_width = 800  # Set your desired fixed width
            canvas_height = 600  # Set your desired fixed height

            self.canvas.config(scrollregion=(0, 0, img.width, img.height))
            self.canvas.config(width=canvas_width, height=canvas_height)

            self.image_path = image_path

            # Use ImageTk.PhotoImage for handling JPEG images
            img_tk = ImageTk.PhotoImage(img)

            self.canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
            self.canvas.image = img_tk


    def run(self):
        self.root.mainloop()
        
def get_dropdown_input(options, title,master):
    # Create a Toplevel window for the custom dialog
    dialog = tk.Toplevel(master)
    dialog.title(title)

    # Create a StringVar to store the selected value
    selected_value = tk.StringVar()

    # Create a Label
    label = tk.Label(dialog, text=f"Select an option for {title}:")
    label.pack(padx=10, pady=5)

    # Create a Combobox
    dropdown = ttk.Combobox(dialog, values=options, textvariable=selected_value)
    dropdown.pack(padx=10, pady=5)

    # Create an OK button to close the dialog
    ok_button = tk.Button(dialog, text="OK", command=dialog.destroy)
    ok_button.pack(pady=10)

    cancel_button = tk.Button(dialog, text="Cancel", command=dialog.destroy)
    cancel_button.pack(side=tk.RIGHT, padx=5)

    # Run the dialog
    dialog.transient(master)
    dialog.grab_set()
    master.wait_window(dialog)

    # Return the selected value
    return selected_value.get() if selected_value.get() else None


class ScreenshotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Screenshot App")

        self.category_manager = CategoryManager()

        self.organizer=Organizer()

        self.current_category_id = None
        self.index=-1

        self.screenshot_handler = ScreenshotHandler(key='.', duration=float('inf'))

        self.setup_gui()

    def setup_gui(self):
        # Set up the main buttons

        self.category_label = tk.Label(self.root, text="Selected Category: None")
        self.category_label.pack(pady=5)

        button_style = 'TButton'
        small_button_style = 'Small.TButton'

        style = ttk.Style()
        
        style.configure(small_button_style, font=('calibri', 9, 'bold'), 
                borderwidth='2', relief="flat", background="lightgray")

        self.select_category_button = ttk.Button(self.root, text="Select Category", command=self.select_category, style=small_button_style)
        self.select_category_button.pack(pady=2)

        self.take_screenshot_button = ttk.Button(self.root, text="Take Screenshot", command=self.take_screenshot, style=small_button_style)
        self.take_screenshot_button.pack(pady=2)

        self.view_screenshots_button = ttk.Button(self.root, text="View/Edit Screenshots", command=self.view_and_edit_screenshots, style=small_button_style)
        self.view_screenshots_button.pack(pady=2)

        self.create_category_button = ttk.Button(self.root, text="Create Category", command=self.create_category, style=small_button_style)
        self.create_category_button.pack(pady=2)

        self.activate_screenshot_handler_button = ttk.Button(self.root, text="Activate Screenshot Handler", command=self.activate_screenshot_handler, style=small_button_style)
        self.activate_screenshot_handler_button.pack(pady=2)

        self.delete_button = ttk.Button(self.root, text="Delete", command=self.delete, style=small_button_style)
        self.delete_button.pack(pady=2)
        # Explicit event bindings
        self.root.bind("<Control-c>", self.create_category)
        self.root.bind("<Control-t>", self.take_screenshot)
        self.root.bind("<Control-v>", self.view_and_edit_screenshots)
        self.root.bind("<Left>",self.view_l_s)
        self.root.bind("<Right>",self.view_r_s)

        # Set up the Paint App
        self.paint_app = PaintApp(self.root)
######################################################################################

    def select_category(self):
        category_id=None
        options=self.category_manager.get_all_senior_categories()
        while options:
            options_names=[cat[0] for cat in options]
            options_id=[cat[1] for cat in options]
            category_name=get_dropdown_input(options_names,"Select Category",self.root)
            if category_name:
                for i in options:
                    if i[0]==category_name:
                        category_id=i[1]
                        options=self.category_manager.get_all_children_categories(category_id)
            else:
                break
    
        if category_id:
            self.current_category_id = category_id
        self.update_category_label()
            
    def create_category(self,event=None):
        # Implement the logic to create a category
        category_name = simpledialog.askstring("Create Category", "Enter Category Name:")
        if category_name:
            if self.current_category_id:
                self.current_category_id, _ = self.category_manager.create_subcategory(category_name,self.current_category_id)
            else:
                self.current_category_id, _ = self.category_manager.create_category(category_name)
        self.update_category_label()

#####################################################  

    def take_screenshot(self,event=None):
        # Implement the logic to take a screenshot and save it in the chosen directory
        if self.current_category_id is not None:
            screenshot_name = simpledialog.askstring("Take Screenshot", "Enter Screenshot Name:") #also ask for annotation
            annotation =simpledialog.askstring("Annotate","Enter annotation")
            if screenshot_name:
                screenshot = ScreenShot(screenshot_name, self.current_category_id, annotation)
                screenshot.capture_and_save()
        else:
            tk.messagebox.showwarning("No directory selected", "Not selected category.")

    def view_and_edit_screenshots(self,event=None):
        # Implement the logic to view screenshots
        if self.current_category_id is not None:
            screenshots = self.organizer.get_screenshots_in_category(self.current_category_id)  
            screenshot_name=get_dropdown_input(screenshots,"view or edit",self.root)
            if screenshot_name:
                # Load the selected screenshot for viewing
                image_path = os.path.join(self.organizer.get_category_path(self.current_category_id), f"{screenshot_name}.png")
                self.paint_app.load_image(image_path)
                self.index=screenshots.index((screenshot_name,))
        else:
            tk.messagebox.showwarning("No directory selected", "Not selected category.")

    def view_l_s(self,event=None):
        if self.index>0:self.index-=1
        if self.current_category_id:
            screenshots = self.organizer.get_screenshots_in_category(self.current_category_id)
            try:
                screenshot_name=screenshots[self.index][0]
                if screenshot_name:
                # Load the selected screenshot for viewing
                    image_path = os.path.join(self.organizer.get_category_path(self.current_category_id), f"{screenshot_name}.png")
                    self.paint_app.load_image(image_path)
            except:
                tk.messagebox.showwarning("some error occured","check the directory may be empty")
        else:
            tk.messagebox.showwarning("No directory selected", "Not selected category.")

    def view_r_s(self,event=None):

        if self.current_category_id:
            screenshots = self.organizer.get_screenshots_in_category(self.current_category_id)
            if self.index<len(screenshots)-1:self.index+=1
            try:
                screenshot_name=screenshots[self.index][0]
                if screenshot_name:
                # Load the selected screenshot for viewing
                    image_path = os.path.join(self.organizer.get_category_path(self.current_category_id), f"{screenshot_name}.png")
                    self.paint_app.load_image(image_path)
            except:
                tk.messagebox.showwarning("some error occured","check the directory may be empty")
        else:
            tk.messagebox.showwarning("No directory selected", "Not selected category.")

    def activate_screenshot_handler(self):
        if self.current_category_id is not None:
            base_name = simpledialog.askstring("Activate Screenshot Handler", "Enter Base Name for Screenshots:")
            if base_name:
                annotation = simpledialog.askstring("Annotate", "Enter annotation")
                self.screenshot_handler.activate(base_name, self.current_category_id, annotation)
        else:
            tk.messagebox.showwarning("No directory selected", "Not selected category.")

    def update_category_label(self):
        category_name = self.organizer.get_category_name(self.current_category_id)
        self.category_label.config(text=f"Selected Category: {category_name}" if category_name else "Selected Category: None")

    def delete(self):
        if self.current_category_id is not None:
            screenshots = self.organizer.get_screenshots_in_category(self.current_category_id)
            
            try:
                screenshot_name = screenshots[self.index][0]
                screenshot_id = self.organizer.get_screenshot_id_by_name(screenshot_name,self.current_category_id)

                if screenshot_id is not None:
                    # Use the delete_screenshot method from the Organizer class
                    self.organizer.delete_screenshot(screenshot_id)
                    print(f"Screenshot '{screenshot_name}' deleted successfully.")

            except IndexError:
                tk.messagebox.showwarning("No screenshot selected", "Please select a screenshot to delete.")
            except Exception as e:
                print(f"Error deleting screenshot: {e}")
            self.view_l_s()
            
                

    


def run_gui():
    root = tk.Tk()
    app = ScreenshotApp(root)
    root.mainloop()

if __name__ == "__main__":
    run_gui()
