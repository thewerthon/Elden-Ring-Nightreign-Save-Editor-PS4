import csv
import json
import os
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk, filedialog, messagebox, simpledialog, Scrollbar
from functools import wraps
from time import time
import hashlib
import binascii
import shutil

hex_pattern1_Fixed = "FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF" #inventory
souls_distance = -1080  # Distance from the found hex pattern to the souls value
possible_name_distances_for_name_tap= [-1132]  #  distances from the found hex pattern to the character name
hex_pattern_end= 'FF FF FF FF'
found_slots = []  # Store found slots for editing
current_slot_index = 0  # Track which slot is currently selected

window = tk.Tk()
window.title("Elden Ring NightReign Save Editor")

try:
    # Set Theme Path
    azure_path = os.path.join(os.path.dirname(__file__), "Resources/Azure", "azure.tcl")
    window.tk.call("source", azure_path)
    window.tk.call("set_theme", "dark")  # or "light" for light theme
except tk.TclError as e:
    messagebox.showwarning("Theme Warning", f"Azure theme could not be loaded: {str(e)}")
file_path_var = tk.StringVar()
current_name_var = tk.StringVar(value="N/A")
new_name_var = tk.StringVar()
current_souls_var = tk.StringVar(value="N/A")
new_souls_var = tk.StringVar()
current_section_var = tk.IntVar(value=0)
loaded_file_data = None

working_directory = os.path.dirname(os.path.abspath(__file__))
os.chdir(working_directory)

def read_file_section(file_path, start_offset, end_offset):
    try:
        with open(file_path, 'rb') as file:
            file.seek(start_offset)
            section_data = file.read(end_offset - start_offset + 1)
        return section_data
    except IOError as e:
        messagebox.showerror("Error", f"Failed to read file section: {str(e)}")
        return None

def find_hex_offset(section_data, hex_pattern):
    try:
        pattern_bytes = bytes.fromhex(hex_pattern)
        if pattern_bytes in section_data:
            return section_data.index(pattern_bytes)
        return None
    except ValueError as e:
        messagebox.showerror("Error", f"Failed to find hex pattern: {str(e)}")
        return None

def calculate_relative_offset(section_start, offset):
    return section_start + offset

def find_value_at_offset(section_data, offset, byte_size=4):
    try:
        value_bytes = section_data[offset:offset+byte_size]
        if len(value_bytes) == byte_size:
            return int.from_bytes(value_bytes, 'little')
    except IndexError:
        pass
    return None

def find_character_name(section_data, offset, byte_size=32):
    try:
        value_bytes = section_data[offset:offset+byte_size]
        name_chars = []
        for i in range(0, len(value_bytes), 2):
            char_byte = value_bytes[i]
            if char_byte == 0:
                break
            if 32 <= char_byte <= 126:
                name_chars.append(chr(char_byte))
            else:
                name_chars.append('.')
        return ''.join(name_chars)
    except IndexError:
        return "N/A"
    
def open_file():
    global loaded_file_data, SECTIONS
    file_path = filedialog.askopenfilename(filetypes=[("Save Files", "*")])
    
    if file_path:
        file_name = os.path.basename(file_path)
        file_path_var.set(file_path)
        file_name_label.config(text=f"File: {file_name}")
        
        # Define sections based on file name
        if file_name.lower() == "memory.dat":
            SECTIONS = {
                1: {'start': 0x80, 'end': 0x10007F},
                2: {'start': 0x100080, 'end': 0x20007F},
                3: {'start': 0x200080, 'end': 0x30007F},
                4: {'start': 0x300080, 'end': 0x40007F},
                5: {'start': 0x400080, 'end': 0x50007F},
                6: {'start': 0x500080, 'end': 0x60007F},
                7: {'start': 0x600080, 'end': 0x70007F},
                8: {'start': 0x700080, 'end': 0x80007F},
                9: {'start': 0x800080, 'end': 0x90007F},
                10: {'start': 0x900080, 'end': 0xA0007F}
            }
        elif file_name.lower() == "er0000.sl2": ## to be done, no decrypted file available
            SECTIONS = {
                1: {'start': 0x310, 'end': 0x28030F},
                2: {'start': 0x280320, 'end': 0x50031F},
                3: {'start': 0x500330, 'end': 0x78032F},
                4: {'start': 0x780340, 'end': 0xA0033F},
                5: {'start': 0xA00350, 'end': 0xC8034F},
                6: {'start': 0xC80360, 'end': 0xF0035F},
                7: {'start': 0xF00370, 'end': 0x118036F},
                8: {'start': 0x1180380, 'end': 0x140037F},
                9: {'start': 0x1400390, 'end': 0x168038F},
                10: {'start': 0x16803A0, 'end': 0x190039F}
            }
        try:
            with open(file_path, 'rb') as file:
                loaded_file_data = file.read()
            
            # Create a backup
            backup_path = f"{file_path}.bak"
            if not os.path.exists(backup_path):
                with open(backup_path, 'wb') as backup_file:
                    backup_file.write(loaded_file_data)
                print(f"Backup created: {backup_path}")
            
            # messagebox.showinfo("Backup Created", f"Backup saved as {backup_path}")
            
            # Enable section buttons
            for btn in section_buttons:
                btn.config(state=tk.NORMAL)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read file or create backup: {str(e)}")
            return

def calculate_offset2(offset1, distance):
    return offset1 + distance

found_slots = []  # Store found slots for editing
current_slot_index = 0  # Track which slot is currently selected
items_json = {}  # Load from your items JSON file
effects_json = {}  # Load from your effects JSON file

def load_json_data():
    global items_json, effects_json
    try:
        file_path = os.path.join(working_directory, "Resources/Json")
        with open(os.path.join(file_path, 'items.json'), 'r') as f:
            items_json = json.load(f)
        with open(os.path.join(file_path, 'effects.json'), 'r') as f:
            effects_json = json.load(f)
    except FileNotFoundError:
        print("JSON files not found. Manual editing only will be available.")
        items_json = {}
        effects_json = {}

def load_section(section_number):
    if not loaded_file_data:
        messagebox.showerror("Error", "Please open a file first")
        return

    current_section_var.set(section_number)
    section_info = SECTIONS[section_number]
    section_data = loaded_file_data[section_info['start']:section_info['end']+1]

    # Try to find hex pattern in the section
    offset1 = find_hex_offset(section_data, hex_pattern1_Fixed)
    if offset1 is not None:
        # Display Souls value
        souls_offset = offset1 + souls_distance
        current_souls = find_value_at_offset(section_data, souls_offset)
        current_souls_var.set(current_souls if current_souls is not None else "N/A")

        # Display character name
        for distance in possible_name_distances_for_name_tap:
            name_offset = offset1 + distance
            current_name = find_character_name(section_data, name_offset)
            if current_name and current_name != "N/A":
                current_name_var.set(current_name)
                break
        else:
            current_name_var.set("N/A")

    else:
        current_souls_var.set("N/A")
        current_name_var.set("N/A")

def write_value_at_offset(file_path, offset, value, byte_size=4):
    value_bytes = value.to_bytes(byte_size, 'little')
    with open(file_path, 'r+b') as file:
        file.seek(offset)
        file.write(value_bytes)

def update_souls_value():
    file_path = file_path_var.get()
    section_number = current_section_var.get()
    
    if not file_path or not new_souls_var.get() or section_number == 0:
        messagebox.showerror("Input Error", "Please open a file and select a section!")
        return
    
    try:
        new_souls_value = int(new_souls_var.get())
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter a valid decimal number for Souls.")
        return

    section_info = SECTIONS[section_number]
    section_data = loaded_file_data[section_info['start']:section_info['end']+1]
    offset1 = find_hex_offset(section_data, hex_pattern1_Fixed)
    
    if offset1 is not None:
        souls_offset = offset1 + souls_distance
        write_value_at_offset(file_path, section_info['start'] + souls_offset, new_souls_value)
        messagebox.showinfo("Success", f"Souls value updated to {new_souls_value}. Reload section to verify.")
    else:
        messagebox.showerror("Pattern Not Found", "Pattern not found in the selected section.")

## Fixed replacing logic
def empty_slot_finder_aow(file_path, pattern_offset_start, pattern_offset_end):
    global found_slots 
    
    def get_slot_size(b4):
        if b4 == 0xC0:
            return 72
        elif b4 == 0x90:
            return 16
        elif b4 == 0x80:
            return 80
        else:
            return None
    
    start_pos = pattern_offset_start
    end_pos = pattern_offset_end
    valid_b4_values = {0x80, 0x90, 0xC0}
    
    try:
        with open(file_path, 'rb') as file:
            file.seek(start_pos)
            section_data = file.read(end_pos - start_pos)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    print(f"[DEBUG] Loaded section of {len(section_data)} bytes from {start_pos} to {end_pos}")

    # Clear previous results
    found_slots.clear()

    # STEP 1: Find alignment point by scanning for valid slots
    def is_valid_slot_start(pos):
        """Check if position could be the start of a valid slot"""
        if pos + 4 > len(section_data):  # Need at least 4 bytes
            return False, None
        
        b3, b4 = section_data[pos+2], section_data[pos+3]
        if b3 == 0x80 and b4 in valid_b4_values:
            slot_size = get_slot_size(b4)
            if slot_size and pos + slot_size <= len(section_data):
                return True, slot_size
        return False, None
    
    # Find the first valid slot
    start_offset = None
    for i in range(0, len(section_data) - 8):  # At least 8 bytes for empty slot check
        valid, first_slot_size = is_valid_slot_start(i)
        if valid:
            # Check if the next position after this slot also starts a valid slot
            next_pos = i + first_slot_size
            valid_next, _ = is_valid_slot_start(next_pos)
            
            # Or check if it's an empty slot (which is also valid)
            is_empty_next = (next_pos + 8 <= len(section_data) and 
                             section_data[next_pos:next_pos+8] == b'\x00\x00\x00\x00\xFF\xFF\xFF\xFF')
            
            if valid_next or is_empty_next:
                start_offset = i
                print(f"[DEBUG] Found valid slot alignment at offset {i}")
                break
    
    if start_offset is None:
        print("[ERROR] No valid slot alignment found.")
        return

    # STEP 2: Process all slots from alignment with variable slot sizes
    valid_slot_count = 0
    i = start_offset

    while i < len(section_data) - 4:
        # Check if this is a valid slot
        if i + 4 <= len(section_data):
            b3, b4 = section_data[i+2], section_data[i+3]

            if b3 == 0x80 and b4 in valid_b4_values:
                slot_size = get_slot_size(b4)

                if slot_size and i + slot_size <= len(section_data):
                    valid_slot_count += 1

                    if b4 == 0xC0:
                        slot_data = section_data[i:i+slot_size]
                        
                        # Extract item ID (bytes 5-7 and 9-11, should be the same)
                        item_id_bytes = slot_data[4:7]  # 5th, 6th, 7th bytes (0-indexed)
                        item_id = int.from_bytes(item_id_bytes, byteorder='little')
                        
                        # Extract effect IDs
                        effect1_bytes = slot_data[16:20]  # 17th to 20th bytes (0-indexed)
                        effect2_bytes = slot_data[20:24]  # 21st to 24th bytes
                        effect3_bytes = slot_data[24:28]  # 25th to 28th bytes
                        
                        effect1_id = int.from_bytes(effect1_bytes, byteorder='little')
                        effect2_id = int.from_bytes(effect2_bytes, byteorder='little')
                        effect3_id = int.from_bytes(effect3_bytes, byteorder='little')
                        
                        slot_info = {
                            'offset': start_pos + i,  # Absolute offset in file
                            'size': slot_size,
                            'data': slot_data.hex(),
                            'raw_data': slot_data,
                            'item_id': item_id,
                            'effect1_id': effect1_id,
                            'effect2_id': effect2_id,
                            'effect3_id': effect3_id
                        }
                        found_slots.append(slot_info)
                        
                        # print(f"[DEBUG] Found valid slot with b4=0xC0 at offset {i}, size {slot_size} bytes.")
                        # print(f"Item ID: {item_id}, Effects: {effect1_id}, {effect2_id}, {effect3_id}")

                    i += slot_size
                    continue
        
        # Check for empty slots
        if i + 8 <= len(section_data) and section_data[i:i+8] == b'\x00\x00\x00\x00\xFF\xFF\xFF\xFF':
            # print(f"[DEBUG] Found empty slot at offset {i}")
            i += 8  # Empty slots are typically 8 bytes
            continue
            
        # If we reach here, this position doesn't match any known pattern
        # Try the next byte position
        i += 1
    
    print(f"[DEBUG] Found {len(found_slots)} slots with b4=0xC0")
    
    # Update the replace tab with found slots
    update_replace_tab()

def find_and_replace_pattern_with_aow_and_update_counters():
    global loaded_file_data
    try:
        # Get file path
        file_path = file_path_var.get()
        section_number = current_section_var.get()
        if not file_path or section_number == 0:
            messagebox.showerror("Error", "No file selected or section not chosen. Please load a file and select a section.")
            return

        # Get section information
        section_info = SECTIONS[section_number]
        
        # Convert loaded_file_data to bytearray if it's not already
        if isinstance(loaded_file_data, bytes):
            loaded_file_data = bytearray(loaded_file_data)
        
        # Get current section data from loaded_file_data
        section_data = loaded_file_data[section_info['start']:section_info['end']+1]

        # Locate Fixed Pattern 1
        fixed_pattern_offset = find_hex_offset(section_data, hex_pattern1_Fixed)
        
        if fixed_pattern_offset is None:
            messagebox.showerror("Error", "Fixed Pattern 1 not found in the selected section.")
            return
            
        fixed_pattern_offset_start = fixed_pattern_offset
        search_start_position = fixed_pattern_offset_start + len(hex_pattern1_Fixed) + 1000
        
        if search_start_position >= len(section_data):
            print("Search start position beyond section data.")
            return
            
        fixed_pattern_offset_end = find_hex_offset(section_data[search_start_position:], hex_pattern_end)
        if fixed_pattern_offset_end is not None:
            fixed_pattern_offset_end += search_start_position
        else:
            # Handle case where end pattern isn't found
            print("End pattern not found")
            return

        # Call the slot finder with corrected parameters
        empty_slot_finder_aow(file_path, section_info['start'] + 32, section_info['start'] + fixed_pattern_offset - 431)

    except Exception as e:
        messagebox.showerror("Error", f"Failed to add or update item: {e}")

def update_replace_tab():
    global current_slot_index
    
    if not found_slots:
        slot_info_text.delete(1.0, tk.END)
        slot_info_text.insert(1.0, "No slots with b4=0xC0 found.")
        # Clear all entry fields
        item_id_entry.delete(0, tk.END)
        effect1_entry.delete(0, tk.END)
        effect2_entry.delete(0, tk.END)
        effect3_entry.delete(0, tk.END)
        slot_navigation_label.config(text="No slots available")
        return
    
    # Reset to first slot if current index is out of bounds
    if current_slot_index >= len(found_slots):
        current_slot_index = 0
    
    # Display current slot info
    slot = found_slots[current_slot_index]
    slot_info_text.delete(1.0, tk.END)
    slot_info_text.insert(1.0, f"Slot {current_slot_index + 1} of {len(found_slots)}\n")
    slot_info_text.insert(tk.END, f"Offset: {slot['offset']} (0x{slot['offset']:X})\n")
    slot_info_text.insert(tk.END, f"Size: {slot['size']} bytes\n")
    slot_info_text.insert(tk.END, f"Raw Data: {slot['data'][:32]}...")  # Show first 32 chars
    
    # Update entry fields with current slot data
    item_id_entry.delete(0, tk.END)
    item_id_entry.insert(0, str(slot['item_id']))
    
    effect1_entry.delete(0, tk.END)
    effect1_entry.insert(0, str(slot['effect1_id']))
    
    effect2_entry.delete(0, tk.END)
    effect2_entry.insert(0, str(slot['effect2_id']))
    
    effect3_entry.delete(0, tk.END)
    effect3_entry.insert(0, str(slot['effect3_id']))
    
    # Update navigation label
    slot_navigation_label.config(text=f"Slot {current_slot_index + 1} of {len(found_slots)}")

def navigate_slot(direction):
    global current_slot_index
    
    if not found_slots:
        return
    
    if direction == "prev":
        current_slot_index = (current_slot_index - 1) % len(found_slots)
    elif direction == "next":
        current_slot_index = (current_slot_index + 1) % len(found_slots)
    
    update_replace_tab()

def open_item_selector():
    if not items_json:
        messagebox.showwarning("Warning", "Items JSON not loaded. Please load items.json file.")
        return
    
    selector_window = tk.Toplevel(window)
    selector_window.title("Select Item")
    selector_window.geometry("400x500")
    
    # Create listbox with scrollbar
    frame = tk.Frame(selector_window)
    frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side="right", fill="y")
    
    listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set)
    listbox.pack(side="left", fill="both", expand=True)
    
    scrollbar.config(command=listbox.yview)
    
    # Populate listbox with items
    for item_id, item_data in items_json.items():
        item_name = item_data.get('name', f'Item {item_id}')
        listbox.insert(tk.END, f"{item_id}: {item_name}")
    
    def select_item():
        selection = listbox.curselection()
        if selection:
            item_text = listbox.get(selection[0])
            item_id = item_text.split(':')[0]
            item_id_entry.delete(0, tk.END)
            item_id_entry.insert(0, item_id)
            selector_window.destroy()
    
    tk.Button(selector_window, text="Select", command=select_item).pack(pady=10)

def open_effect_selector(effect_entry):
    if not effects_json:
        messagebox.showwarning("Warning", "Effects JSON not loaded. Please load effects.json file.")
        return
    
    selector_window = tk.Toplevel(window)
    selector_window.title("Select Effect")
    selector_window.geometry("400x500")
    
    # Create listbox with scrollbar
    frame = tk.Frame(selector_window)
    frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side="right", fill="y")
    
    listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set)
    listbox.pack(side="left", fill="both", expand=True)
    
    scrollbar.config(command=listbox.yview)
    
    # Populate listbox with effects
    for effect_id, effect_data in effects_json.items():
        effect_name = effect_data.get('name', f'Effect {effect_id}')
        listbox.insert(tk.END, f"{effect_id}: {effect_name}")
    
    def select_effect():
        selection = listbox.curselection()
        if selection:
            effect_text = listbox.get(selection[0])
            effect_id = effect_text.split(':')[0]
            effect_entry.delete(0, tk.END)
            effect_entry.insert(0, effect_id)
            selector_window.destroy()
    
    tk.Button(selector_window, text="Select", command=select_effect).pack(pady=10)

def apply_slot_changes():
    global loaded_file_data, found_slots, current_slot_index
    
    if not found_slots or current_slot_index >= len(found_slots):
        messagebox.showerror("Error", "No slot selected for editing.")
        return
    
    try:
        # Get values from entry fields
        new_item_id = int(item_id_entry.get())
        new_effect1_id = int(effect1_entry.get())
        new_effect2_id = int(effect2_entry.get())
        new_effect3_id = int(effect3_entry.get())
        
        current_slot = found_slots[current_slot_index]
        
        # Create a copy of the raw data to modify
        new_slot_data = bytearray(current_slot['raw_data'])
        
        # Update item ID in bytes 5-7 and 9-11 (0-indexed as 4-6 and 8-10)
        item_id_bytes = new_item_id.to_bytes(3, byteorder='little')
        new_slot_data[4:7] = item_id_bytes  # 5th, 6th, 7th bytes
        new_slot_data[8:11] = item_id_bytes  # 9th, 10th, 11th bytes (duplicate)
        
        # Update effect IDs
        effect1_bytes = new_effect1_id.to_bytes(4, byteorder='little')
        effect2_bytes = new_effect2_id.to_bytes(4, byteorder='little')
        effect3_bytes = new_effect3_id.to_bytes(4, byteorder='little')
        
        new_slot_data[16:20] = effect1_bytes  # 17th to 20th bytes
        new_slot_data[20:24] = effect2_bytes  # 21st to 24th bytes
        new_slot_data[24:28] = effect3_bytes  # 25th to 28th bytes
        
        # Get file path
        file_path = file_path_var.get()
        if not file_path:
            messagebox.showerror("Error", "No file loaded.")
            return
        
        # Write changes to file
        with open(file_path, 'r+b') as file:
            file.seek(current_slot['offset'])
            file.write(new_slot_data)
        
        # Update loaded_file_data as well to keep it in sync
        start_idx = current_slot['offset']
        end_idx = start_idx + len(new_slot_data)
        loaded_file_data[start_idx:end_idx] = new_slot_data
        
        # Update the slot data in our tracking
        current_slot['data'] = new_slot_data.hex()
        current_slot['raw_data'] = new_slot_data
        current_slot['item_id'] = new_item_id
        current_slot['effect1_id'] = new_effect1_id
        current_slot['effect2_id'] = new_effect2_id
        current_slot['effect3_id'] = new_effect3_id
        
        # Refresh the display
        update_replace_tab()
        
        messagebox.showinfo("Success", f"Slot {current_slot_index + 1} updated successfully!")
        
    except ValueError:
        messagebox.showerror("Error", "Please enter valid integer values for all IDs.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to update slot: {e}")

def import_items_from_csv():

    if not found_slots:
        messagebox.showerror("Error", "No slots loaded. Scan for slots first.")
        return
    
    csv_file_path = filedialog.askopenfilename(
        title="Select CSV File",
        filetypes=[("CSV files", "*.csv")]
    )

    if not csv_file_path:
        return  # Cancelado

    try:
        with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='\t')
            
            for row in reader:
                try:
                    id = int(row['id']) - 1
                    if id < 0 or id >= len(found_slots):
                        print(f"Order {id + 1} is out of range. Skipping.")
                        continue
                    
                    slot = found_slots[id]
                    new_slot_data = bytearray(slot['raw_data'])
                    
                    # Item ID
                    item_id = int(row['item'])
                    item_id_bytes = item_id.to_bytes(3, byteorder='little')
                    new_slot_data[4:7] = item_id_bytes
                    new_slot_data[8:11] = item_id_bytes
                    
                    # Effects
                    for idx, eff_offset in enumerate(range(16, 28, 4)):
                        effect_col = f'effect{idx+1}'
                        effect_id = int(row.get(effect_col, 0))
                        effect_bytes = effect_id.to_bytes(4, byteorder='little')
                        new_slot_data[eff_offset:eff_offset+4] = effect_bytes
                    
                    # Write to file
                    with open(file_path_var.get(), 'r+b') as file:
                        file.seek(slot['offset'])
                        file.write(new_slot_data)
                    
                    # Update loaded data in memory
                    start_idx = slot['offset']
                    end_idx = start_idx + len(new_slot_data)
                    loaded_file_data[start_idx:end_idx] = new_slot_data

                    # Update slot info
                    slot['raw_data'] = new_slot_data
                    slot['data'] = new_slot_data.hex()
                    slot['item_id'] = item_id
                    for idx in range(5):
                        slot[f'effect{idx+1}_id'] = int(row.get(f'effect{idx+1}', 0))
                    
                    print(f"Updated slot {id + 1} successfully.")
                    
                except Exception as ex:
                    print(f"Error processing row {row}: {ex}")
        
        messagebox.showinfo("Import Complete", "CSV import completed successfully.")
        update_replace_tab()

    except Exception as e:
        messagebox.showerror("Error", f"Failed to import CSV: {e}")

##UI stuff
file_open_frame = tk.Frame(window)
file_open_frame.pack(fill="x", padx=10, pady=5)

tk.Button(file_open_frame, text="Open Save File", command=open_file).pack(side="left", padx=5)
file_name_label = tk.Label(file_open_frame, text="No file selected", anchor="w")
file_name_label.pack(side="left", padx=10, fill="x")

section_frame = tk.Frame(window)
section_frame.pack(fill="x", padx=10, pady=5)
section_buttons = []
for i in range(1, 11):
    btn = tk.Button(section_frame, text=f"Slot {i}", command=lambda x=i: load_section(x), state=tk.DISABLED)
    btn.pack(side="left", padx=5)
    section_buttons.append(btn)

notebook = ttk.Notebook(window)

# Name tab
name_tab = ttk.Frame(notebook)
notebook.add(name_tab, text="Name")
ttk.Label(name_tab, text="Current Character Name:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
ttk.Label(name_tab, textvariable=current_name_var).grid(row=0, column=1, padx=10, pady=10)

souls_tab = ttk.Frame(notebook)
notebook.add(souls_tab, text="Murks/Runes")
ttk.Label(souls_tab, text="Current Souls:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
ttk.Label(souls_tab, textvariable=current_souls_var).grid(row=0, column=1, padx=10, pady=10)
ttk.Label(souls_tab, text="New Souls Value (MAX 999999999):").grid(row=1, column=0, padx=10, pady=10, sticky="e")
ttk.Entry(souls_tab, textvariable=new_souls_var, width=20).grid(row=1, column=1, padx=10, pady=10)
ttk.Button(souls_tab, text="Update Souls", command=update_souls_value).grid(row=2, column=0, columnspan=2, pady=20)

# Replace tab
replace_tab = ttk.Frame(notebook)
notebook.add(replace_tab, text="Replace")
tk.Button(replace_tab, text="Scan for Relics", command=find_and_replace_pattern_with_aow_and_update_counters).grid(row=0, column=0, columnspan=2, pady=20)

# Slot information display
ttk.Label(replace_tab, text="Slot Information:").grid(row=0, column=0, columnspan=4, padx=10, pady=5, sticky="w")
slot_info_text = tk.Text(replace_tab, height=4, width=60, state=tk.NORMAL)
slot_info_text.grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky="ew")

# Navigation controls
nav_frame = tk.Frame(replace_tab)
nav_frame.grid(row=2, column=0, columnspan=4, pady=10)

tk.Button(nav_frame, text="← Previous", command=lambda: navigate_slot("prev")).pack(side="left", padx=5)
slot_navigation_label = tk.Label(nav_frame, text="No slots available")
slot_navigation_label.pack(side="left", padx=20)
tk.Button(nav_frame, text="Next →", command=lambda: navigate_slot("next")).pack(side="left", padx=5)

# Item ID section
ttk.Label(replace_tab, text="Item ID:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
item_id_frame = tk.Frame(replace_tab)
item_id_frame.grid(row=4, column=0, padx=10, pady=5, sticky="ew")

item_id_entry = tk.Entry(item_id_frame, width=15)
item_id_entry.pack(side="left", padx=(0, 5))
tk.Button(item_id_frame, text="Select from JSON", command=open_item_selector).pack(side="left")

# Effect 1 section
ttk.Label(replace_tab, text="Effect 1 ID:").grid(row=3, column=1, padx=10, pady=5, sticky="w")
effect1_frame = tk.Frame(replace_tab)
effect1_frame.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

effect1_entry = tk.Entry(effect1_frame, width=15)
effect1_entry.pack(side="left", padx=(0, 5))
tk.Button(effect1_frame, text="Select from JSON", command=lambda: open_effect_selector(effect1_entry)).pack(side="left")

# Effect 2 section
ttk.Label(replace_tab, text="Effect 2 ID:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
effect2_frame = tk.Frame(replace_tab)
effect2_frame.grid(row=6, column=0, padx=10, pady=5, sticky="ew")

effect2_entry = tk.Entry(effect2_frame, width=15)
effect2_entry.pack(side="left", padx=(0, 5))
tk.Button(effect2_frame, text="Select from JSON", command=lambda: open_effect_selector(effect2_entry)).pack(side="left")

# Effect 3 section
ttk.Label(replace_tab, text="Effect 3 ID:").grid(row=5, column=1, padx=10, pady=5, sticky="w")
effect3_frame = tk.Frame(replace_tab)
effect3_frame.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

effect3_entry = tk.Entry(effect3_frame, width=15)
effect3_entry.pack(side="left", padx=(0, 5))
tk.Button(effect3_frame, text="Select from JSON", command=lambda: open_effect_selector(effect3_entry)).pack(side="left")

# Create a frame to hold both buttons
button_frame = tk.Frame(replace_tab)
button_frame.grid(row=7, column=0, columnspan=4, pady=20)

# Apply Changes button
tk.Button(button_frame, text="Apply Changes", command=apply_slot_changes, bg="orange", fg="white").pack(side="left", padx=20)

# Import CSV button
tk.Button(button_frame, text="Import from CSV", command=import_items_from_csv, bg="green", fg="white").pack(side="left", padx=20)

# Configure column weights for resizing
replace_tab.columnconfigure(0, weight=1)
replace_tab.columnconfigure(1, weight=1)

notebook.pack(expand=1, fill="both")

# Load JSON data on startup
load_json_data()

my_label = tk.Label(window, text="Made by Alfazari911 --   Thanks to Nox and BawsDeep for help", anchor="e", padx=10)
my_label.pack(side="top", anchor="ne", padx=10, pady=5)

we_label = tk.Label(window, text="USE AT YOUR OWN RISK. EDITING STATS AND HP COULD GET YOU BANNED", anchor="w", padx=10)
we_label.pack(side="bottom", anchor="nw", padx=10, pady=5)

# Run 
window.mainloop()
