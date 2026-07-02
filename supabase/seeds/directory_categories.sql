-- ============================================================
-- Seed: Pre-built Directory Definitions
-- ============================================================

INSERT INTO directories (slug, title, description, filter_config, meta_title, meta_description) VALUES

-- COLOR-BASED DIRECTORIES
('red-limos',
 'Red Limousines in the USA',
 'Browse every red limousine company across the United States. Find the boldest rides for proms, birthdays, and special occasions.',
 '{"vehicle_color": "red", "vehicle_type_slugs": ["stretch_limo", "hummer_limo", "suv_limo"]}',
 'Red Limos in the USA | Limo Directory',
 'Find red limousine companies near you. Browse verified red limo services for prom, weddings, and more.'),

('black-limos',
 'Black Limousines in the USA',
 'Classic black limousines for corporate events, weddings, and airport transfers.',
 '{"vehicle_color": "black", "vehicle_type_slugs": ["stretch_limo", "suv_limo", "sedan"]}',
 'Black Limos in the USA | Limo Directory',
 'Find black limousine companies near you. Elegant black limos for every occasion.'),

('white-limos',
 'White Limousines in the USA',
 'Pristine white limousines — the classic choice for weddings and proms.',
 '{"vehicle_color": "white", "vehicle_type_slugs": ["stretch_limo", "hummer_limo"]}',
 'White Limos in the USA | Limo Directory',
 'Browse white limousine services near you. Perfect for weddings, proms, and quinceañeras.'),

('silver-limos',
 'Silver & Champagne Limousines',
 'Sophisticated silver and champagne limousines for upscale events.',
 '{"vehicle_color": "silver", "vehicle_type_slugs": ["stretch_limo", "suv_limo", "sedan"]}',
 'Silver Limos in the USA | Limo Directory',
 'Find silver and champagne limousine services across the USA.'),

-- EVENT-BASED DIRECTORIES
('wedding-party-buses',
 'Wedding Party Buses in the USA',
 'Spacious party buses designed for wedding transportation. Move your entire bridal party in style.',
 '{"event_type_slugs": ["wedding"], "vehicle_type_slugs": ["party_bus", "mini_bus", "double_decker"]}',
 'Wedding Party Buses | Limo Directory',
 'Find wedding party bus services near you. Perfect for bridal parties, rehearsal dinners, and wedding days.'),

('wedding-limos',
 'Wedding Limousines in the USA',
 'Classic and elegant limousines for your wedding day.',
 '{"event_type_slugs": ["wedding"], "vehicle_type_slugs": ["stretch_limo", "vintage", "sedan"]}',
 'Wedding Limos in the USA | Limo Directory',
 'Browse wedding limousine companies near you. Make your wedding day unforgettable.'),

('prom-limos',
 'Prom Limousines in the USA',
 'Make prom night legendary. Find limo companies that specialize in prom transportation for teens.',
 '{"event_type_slugs": ["prom"]}',
 'Prom Limos in the USA | Limo Directory',
 'Find prom limousine services near you. Safe, stylish transportation for prom and homecoming.'),

('prom-party-buses',
 'Prom Party Buses',
 'Party buses for prom groups — the ultimate group prom transportation.',
 '{"event_type_slugs": ["prom"], "vehicle_type_slugs": ["party_bus"]}',
 'Prom Party Buses in the USA | Limo Directory',
 'Find prom party bus services near you. Book a party bus for your prom group.'),

('bachelorette-party-buses',
 'Bachelorette Party Buses',
 'The ultimate bachelorette experience — party buses with full bars, LED lights, and dance floors.',
 '{"event_type_slugs": ["bachelorette"], "vehicle_type_slugs": ["party_bus"]}',
 'Bachelorette Party Buses | Limo Directory',
 'Find bachelorette party bus rentals near you. Make the last night of freedom unforgettable.'),

('birthday-party-buses',
 'Birthday Party Buses',
 'Mobile party venues for birthday celebrations of any size.',
 '{"event_type_slugs": ["birthday"], "vehicle_type_slugs": ["party_bus"]}',
 'Birthday Party Buses in the USA | Limo Directory',
 'Book a birthday party bus near you. The most fun way to celebrate your birthday.'),

('corporate-limos',
 'Corporate Limousine Services',
 'Professional corporate transportation — client pickups, roadshows, and executive travel.',
 '{"event_type_slugs": ["corporate"]}',
 'Corporate Limo Services in the USA | Limo Directory',
 'Find corporate limousine services near you. Professional executive transportation across the USA.'),

('airport-limo-services',
 'Airport Limousine Services',
 'Reliable airport pickup and drop-off services across all major US airports.',
 '{"event_type_slugs": ["airport"]}',
 'Airport Limo Services in the USA | Limo Directory',
 'Find airport limousine services near you. Reliable, on-time airport transfers.'),

('quinceanera-limos',
 'Quinceañera Limousines & Party Buses',
 'Make her quinceañera unforgettable with a stunning limousine or party bus.',
 '{"event_type_slugs": ["quinceañera"]}',
 'Quinceañera Limos in the USA | Limo Directory',
 'Find quinceañera limousine services near you. Make her 15th birthday special.'),

-- VEHICLE TYPE DIRECTORIES
('hummer-limos',
 'Hummer Limousines in the USA',
 'The boldest limos on the road — Hummer limousines for every occasion.',
 '{"vehicle_type_slugs": ["hummer_limo"]}',
 'Hummer Limos in the USA | Limo Directory',
 'Find Hummer limousine services near you. Bold, spacious Hummer limos for every event.'),

('sprinter-van-limos',
 'Sprinter Van Limo Services',
 'Luxury Mercedes-Benz Sprinter vans — the stylish alternative to traditional limos.',
 '{"vehicle_type_slugs": ["sprinter_van"]}',
 'Sprinter Van Limos in the USA | Limo Directory',
 'Find Sprinter van limo services near you. Luxury Sprinter transportation for groups.'),

('vintage-limos',
 'Vintage & Classic Limousines',
 'Antique and classic cars for a timeless, elegant experience.',
 '{"vehicle_type_slugs": ["vintage"]}',
 'Vintage Limos in the USA | Limo Directory',
 'Find vintage and classic limousine services near you. Timeless elegance for special occasions.'),

('wine-tour-limos',
 'Wine Tour Limousine Services',
 'Designated driver included — explore wine country in style.',
 '{"event_type_slugs": ["wine_tour"]}',
 'Wine Tour Limos in the USA | Limo Directory',
 'Find wine tour limousine services near you. Sip, tour, and arrive safely.');