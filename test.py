from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
from datetime import datetime

# ============================================================================
# SETUP AND CONFIGURATION
# ============================================================================

def setup_driver():
    """Initialize Chrome WebDriver with optimal settings"""
    options = webdriver.ChromeOptions()
    # options.add_argument('--headless')  # Uncomment to run in background
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), 
        options=options
    )

# ============================================================================
# ENHANCED SLOT EXTRACTION ENGINE
# ============================================================================

def extract_slots(driver, venue_name, court_name):
    """Extract all slot data from the booking table with enhanced availability detection"""
    wait = WebDriverWait(driver, 10)
    slots_data = []
    
    try:
        print(f"🔍 Extracting slots for: {court_name}")
        print("-" * 50)
        
        time.sleep(2)
        slots_table = driver.find_element(By.CLASS_NAME, "style_table__gYUfm")
        
        # Extract available dates from table headers
        date_elements = slots_table.find_elements(By.CLASS_NAME, "style_date__vVFsu")
        dates = [
            elem.text.strip() 
            for elem in date_elements 
            if elem.text.strip().isdigit() and len(elem.text.strip()) <= 2
        ]
        
        print(f"📅 Available dates: {dates}")
        
        # Get all data rows (excluding header)
        all_rows = slots_table.find_elements(By.XPATH, ".//tr")
        data_rows = all_rows[1:]  # Skip header row
        
        print(f"⏰ Processing {len(data_rows)} time slots...")
        
        # Process each time slot row
        for row_index, row in enumerate(data_rows):
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                
                if len(cells) == 0:
                    continue
                    
                # Extract time from first cell
                time_slot = cells[0].text.strip()
                
                # Skip invalid time slots
                if not time_slot or ("AM" not in time_slot and "PM" not in time_slot):
                    continue
                
                # Process each date column
                data_cells = cells[1:]  # Skip time column
                
                for cell_index, cell in enumerate(data_cells):
                    if cell_index < len(dates):
                        cell_text = cell.text.strip()
                        
                        # Get cell styling/classes for availability detection
                        cell_classes = cell.get_attribute('class') or ""
                        cell_style = cell.get_attribute('style') or ""
                        
                        # Skip completely empty cells
                        if not cell_text or cell_text == "-":
                            continue
                        
                        # Enhanced availability detection
                        price, availability, is_available = parse_slot_data_enhanced(
                            cell_text, cell_classes, cell_style
                        )
                        
                        # Only add slots with meaningful data
                        if price or availability:
                            slot_info = {
                                'venue': venue_name,
                                'court': court_name,
                                'date': dates[cell_index],
                                'time': time_slot,
                                'price': price,
                                'availability': availability,
                                'is_available': is_available,
                                'raw_data': cell_text,
                                'cell_classes': cell_classes,
                                'scraped_at': datetime.now().isoformat()
                            }
                            
                            slots_data.append(slot_info)
                            
            except Exception as e:
                print(f"⚠️  Error processing row {row_index}: {e}")
                continue
        
        # Calculate summary statistics
        available_count = sum(1 for slot in slots_data if slot['is_available'])
        unavailable_count = len(slots_data) - available_count
        
        print(f"✅ Successfully extracted {len(slots_data)} total slots")
        print(f"📊 Available: {available_count} | Unavailable: {unavailable_count}")
        print("-" * 50)
        
        return slots_data
        
    except Exception as e:
        print(f"❌ Error extracting slots: {e}")
        return []

def parse_slot_data_enhanced(cell_text, cell_classes, cell_style):
    """Enhanced parsing with CSS class and style detection for better availability detection"""
    price = ""
    availability = ""
    is_available = False
    
    # Check for disabled/grayed out styling first
    disabled_keywords = ['disabled', 'unavailable', 'booked', 'inactive', 'grey', 'gray']
    if any(keyword in cell_classes.lower() for keyword in disabled_keywords):
        availability = "Unavailable (Disabled)"
        is_available = False
        return price, availability, is_available
    
    # Check for grayed out styling in CSS
    if 'opacity' in cell_style.lower():
        opacity_val = cell_style.lower().split('opacity')[1].split(';')[0].replace(':', '').strip()
        try:
            if float(opacity_val) < 0.5:  # Less than 50% opacity = disabled
                availability = "Unavailable (Grayed Out)"
                is_available = False
                return price, availability, is_available
        except:
            pass
    
    # Standard text-based parsing
    if "₹" in cell_text:
        # Extract price
        price_parts = cell_text.split("₹")
        if len(price_parts) > 1:
            price_num = price_parts[1].split()[0] if price_parts[1].split() else ""
            price = f"₹{price_num}"
        
        # Check availability status
        if "left" in cell_text.lower():
            # Extract the number before "left"
            left_part = cell_text.split("₹")[0].strip()
            
            # Check for "0 left" specifically
            if "0 left" in cell_text.lower():
                availability = "Fully Booked"
                is_available = False
            else:
                availability = left_part
                is_available = True
        else:
            # Has price but no "left" indicator
            availability = "Available"
            is_available = True
            
    elif any(keyword in cell_text.lower() for keyword in ["booked", "unavailable", "closed", "full", "sold out"]):
        # Explicitly unavailable keywords
        availability = "Booked"
        is_available = False
    elif cell_text.strip() == "" or cell_text.strip() == "-" or cell_text.strip() == "N/A":
        # Empty or placeholder cells
        availability = "Not Available"
        is_available = False
    else:
        # Unknown status - be conservative
        availability = f"Unknown ({cell_text})"
        is_available = False
    
    return price, availability, is_available

# ============================================================================
# ENHANCED RESULTS DISPLAY - SHOWING ALL SLOTS
# ============================================================================

def display_all_slots(slots, court_name):
    """Display ALL slots in a beautifully formatted way"""
    print("\n" + "="*80)
    print("                        🎾 ALL AVAILABLE SLOTS 🎾")
    print("="*80)
    
    if not slots:
        print("❌ No slots extracted!")
        print("="*80)
        return
    
    # Calculate statistics
    total_slots = len(slots)
    available_slots = [slot for slot in slots if slot['is_available']]
    unavailable_slots = [slot for slot in slots if not slot['is_available']]
    
    # Group slots by date
    slots_by_date = {}
    for slot in slots:
        date = slot['date']
        if date not in slots_by_date:
            slots_by_date[date] = {'available': [], 'unavailable': []}
        
        if slot['is_available']:
            slots_by_date[date]['available'].append(slot)
        else:
            slots_by_date[date]['unavailable'].append(slot)
    
    # Display summary
    print(f"🏟️  Court: {court_name}")
    print(f"📊 Total Slots: {total_slots}")
    print(f"✅ Available: {len(available_slots)} ({len(available_slots)/total_slots*100:.1f}%)")
    print(f"❌ Unavailable: {len(unavailable_slots)} ({len(unavailable_slots)/total_slots*100:.1f}%)")
    print(f"📅 Date Range: {min(slots_by_date.keys())} - {max(slots_by_date.keys())}")
    
    # Display ALL slots organized by date
    for date in sorted(slots_by_date.keys()):
        date_available = slots_by_date[date]['available']
        date_unavailable = slots_by_date[date]['unavailable']
        total_date_slots = len(date_available) + len(date_unavailable)
        
        print("\n" + "="*80)
        print(f"                           📅 DATE: {date}")
        print(f"     Available: {len(date_available)} | Unavailable: {len(date_unavailable)} | Total: {total_date_slots}")
        print("="*80)
        
        # Show available slots for this date
        if date_available:
            print(f"\n✅ AVAILABLE SLOTS FOR DATE {date}:")
            print("-"*80)
            print(f"{'#':<4} {'Time':<12} {'Price':<10} {'Availability':<25} {'Status':<15}")
            print("-"*80)
            
            for i, slot in enumerate(date_available, 1):
                print(f"{i:<4} {slot['time']:<12} {slot['price']:<10} {slot['availability']:<25} ✅ Available")
        
        # Show unavailable slots for this date
        if date_unavailable:
            print(f"\n❌ UNAVAILABLE SLOTS FOR DATE {date}:")
            print("-"*80)
            print(f"{'#':<4} {'Time':<12} {'Status':<40} {'Reason':<15}")
            print("-"*80)
            
            for i, slot in enumerate(date_unavailable, 1):
                print(f"{i:<4} {slot['time']:<12} {slot['availability']:<40} ❌ Unavailable")
    
    # Overall summary at the end
    print("\n" + "="*80)
    print("                           📊 FINAL SUMMARY")
    print("="*80)
    
    for date in sorted(slots_by_date.keys()):
        date_available = len(slots_by_date[date]['available'])
        date_unavailable = len(slots_by_date[date]['unavailable'])
        date_total = date_available + date_unavailable
        availability_pct = (date_available / date_total * 100) if date_total > 0 else 0
        
        print(f"Date {date}: {date_available:2d} available | {date_unavailable:2d} unavailable | {availability_pct:5.1f}% free")
    
    print("="*80)

def save_results(slots, venue_name, court_name):
    """Save results to a well-formatted JSON file"""
    if not slots:
        print("❌ No data to save!")
        return
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"slots_{venue_name.replace(' ', '_')}_{court_name.replace(' ', '_')}_{timestamp}.json"
    
    # Organize data for better JSON structure
    organized_data = {
        "extraction_info": {
            "venue": venue_name,
            "court": court_name,
            "extraction_time": datetime.now().isoformat(),
            "total_slots": len(slots),
            "available_slots": sum(1 for slot in slots if slot['is_available']),
            "unavailable_slots": sum(1 for slot in slots if not slot['is_available'])
        },
        "slots": slots
    }
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(organized_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filename}")
        print(f"📁 File size: {len(json.dumps(organized_data))} characters")
        
    except Exception as e:
        print(f"❌ Error saving file: {e}")

# ============================================================================
# MAIN TESTING FUNCTION
# ============================================================================

def test_single_court_slots(venue_url, venue_name):
    """Test slot extraction for a single court with enhanced output"""
    print("\n" + "="*80)
    print("                   🏸 PICKLEBALL SLOT EXTRACTION SYSTEM 🏸")
    print("="*80)
    print(f"🎾 Venue: {venue_name}")
    print(f"🔗 URL: {venue_url}")
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    driver = setup_driver()
    wait = WebDriverWait(driver, 10)
    
    try:
        # Step 1: Navigate to venue
        print("\n🌐 Step 1: Navigating to venue...")
        driver.get(venue_url)
        time.sleep(2)
        print("✅ Page loaded successfully")
        
        # Step 2: Click main activity button
        print("\n🎯 Step 2: Looking for main activity button...")
        activity_button = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(@class, 'style_btnBook__vzqXl') and normalize-space(text())='Book']")
            )
        )
        print("✅ Activity button found")
        activity_button.click()
        time.sleep(2)
        print("✅ Activity button clicked")
        
        # Step 3: Find available courts
        print("\n🏟️  Step 3: Searching for available courts...")
        court_buttons = wait.until(EC.presence_of_all_elements_located(
            (By.XPATH, "//button[contains(@class, 'style_btnBook__M3MFK') and normalize-space(text())='Book']")
        ))
        
        print(f"✅ Found {len(court_buttons)} available courts")
        
        if court_buttons:
            # Step 4: Select and process first court
            print("\n🎾 Step 4: Processing first court...")
            first_court = court_buttons[0]
            
            # Extract court name
            try:
                court_container = first_court.find_element(By.XPATH, "./ancestor::div[contains(@class, 'court-card')]")
                court_name = court_container.find_element(By.TAG_NAME, "h3").text.strip()
            except:
                court_name = "Test Court 1"
            
            print(f"🏆 Selected court: {court_name}")
            first_court.click()
            time.sleep(3)
            print("✅ Court selected successfully")
            
            # Step 5: Extract slot data
            print("\n📊 Step 5: Extracting slot information...")
            slots = extract_slots(driver, venue_name, court_name)
            
            # Step 6: Display ALL results
            print("\n🎨 Step 6: Displaying ALL slots...")
            display_all_slots(slots, court_name)
            
            # Step 7: Save data
            print("\n💾 Step 7: Saving data...")
            save_results(slots, venue_name, court_name)
            
            # Step 8: Final summary
            print("\n" + "="*80)
            print("                           🎉 EXTRACTION COMPLETE 🎉")
            print("="*80)
            print(f"✅ Successfully processed: {venue_name} - {court_name}")
            print(f"📊 Total slots found: {len(slots)}")
            print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*80)
            
            # Keep browser open for inspection
            print("\n🔍 Keeping browser open for 15 seconds for manual inspection...")
            time.sleep(15)
            
        else:
            print("❌ No court buttons found!")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        
    finally:
        driver.quit()
        print("\n🏁 Browser closed - Test completed!")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Configuration
    TEST_URL = "" # add venue url here
    VENUE_NAME = "Hot Shot Pickleball Arena"
    
    print("🚀 Starting Pickleball Slot Extraction System...")
    test_single_court_slots(TEST_URL, VENUE_NAME)
