"""
Example-based prompts to help small LLMs understand response patterns.
"""

EXAMPLE_PROMPTS = {
    "general_example": """
When answering questions, follow these examples:

Question: What is photosynthesis?
Answer: Photosynthesis is the process where plants convert sunlight, water, and carbon dioxide into oxygen and glucose. This happens in chloroplasts containing chlorophyll, which absorbs light energy. The glucose provides energy for the plant, while oxygen is released as a byproduct.

Question: Who was Marie Curie?
Answer: Marie Curie (1867-1934) was a pioneering physicist and chemist who discovered the elements polonium and radium. She was the first woman to win a Nobel Prize, the first person to win Nobel Prizes in two different scientific fields, and remains the only person to win in multiple scientific fields. Her work established the theory of radioactivity and techniques for isolating radioactive isotopes.

Question: What is climate change?
Answer: Climate change refers to long-term shifts in temperatures and weather patterns. These changes may be natural, but since the 1800s, human activities have been the main driver, primarily due to burning fossil fuels like coal, oil, and gas, which produces heat-trapping gases. This has led to rising global temperatures, melting ice caps, rising sea levels, and more extreme weather events.""",

    "technical_example": """
When explaining technical concepts, follow these examples:

Question: How does a relational database work?
Answer: A relational database stores data in tables with rows and columns. Each row represents a record, and each column represents an attribute of that record. Tables are related to each other through keys - primary keys uniquely identify records in a table, while foreign keys establish relationships between tables. SQL (Structured Query Language) is used to query and manipulate these tables. When you run a query, the database engine processes it, retrieves the relevant data, and returns the results.

Question: What is object-oriented programming?
Answer: Object-oriented programming (OOP) is a programming paradigm based on the concept of "objects" containing data (attributes) and code (methods). These objects are instances of classes, which serve as blueprints. OOP is built on four main principles: 1) Encapsulation: bundling data and methods that operate on that data, 2) Inheritance: creating new classes from existing ones, 3) Polymorphism: handling objects differently based on their class, and 4) Abstraction: hiding complex implementation details behind simple interfaces.

Question: How does public key encryption work?
Answer: Public key encryption uses a pair of keys - a public key for encryption and a private key for decryption. When someone wants to send you a secure message, they use your public key (which is freely shared) to encrypt it. Once encrypted, the message can only be decrypted using your private key (which only you possess). This system allows secure communication without needing to share secret keys beforehand. The mathematical relationship between the keys makes it computationally infeasible to derive the private key from the public key.""",

    "step_by_step_example": """
When providing step-by-step instructions, follow these examples:

Question: How do I reset my password?
Answer:
1. Go to the login page of the website
2. Click on the "Forgot Password" link (usually below the login form)
3. Enter the email address associated with your account
4. Check your email inbox for a password reset link
5. Click the link in the email (note: these links typically expire after 24 hours)
6. On the new page, enter your new password twice to confirm
7. Click "Submit" or "Save Changes"
8. Try logging in with your new password

Question: How do I change a flat tire?
Answer:
1. Find a safe location to park, away from traffic
2. Apply the parking brake and place wheel wedges
3. Remove the hubcap to access the lug nuts
4. Loosen (but don't remove) the lug nuts with a lug wrench
5. Position the jack under the car at the recommended lifting point
6. Raise the car until the flat tire is about 6 inches off the ground
7. Remove the loosened lug nuts completely
8. Remove the flat tire by pulling it straight toward you
9. Mount the spare tire onto the wheel hub
10. Replace the lug nuts and tighten them by hand
11. Lower the car and remove the jack
12. Fully tighten the lug nuts in a star pattern
13. Replace the hubcap and stow all equipment""",

    "comparison_example": """
When comparing different options, follow these examples:

Question: What's the difference between RAM and ROM?
Answer:
RAM (Random Access Memory):
- Temporary, volatile storage that loses data when power is off
- Used for active programs and data the CPU is currently processing
- Faster access speeds but more expensive per gigabyte
- Can be written to and read from constantly
- Typically ranges from 4GB to 32GB in modern computers

ROM (Read-Only Memory):
- Permanent, non-volatile storage that retains data without power
- Used for essential startup instructions that rarely change
- Slower access speeds but cheaper per gigabyte
- Primarily read-only with limited write capabilities
- Usually just a few megabytes in size

Question: What are the pros and cons of electric vs. gas cars?
Answer:
Electric Cars:
- Pros: Lower operating costs, zero emissions, instant torque, quieter operation
- Cons: Limited range, longer refueling time, fewer charging stations, higher initial cost

Gas Cars:
- Pros: Longer range, quick refueling, widespread infrastructure, lower initial cost
- Cons: Higher maintenance costs, produce emissions, reliance on fossil fuels, noisy operation""",

    "troubleshooting_example": """
When helping with troubleshooting, follow these examples:

Question: My computer won't turn on. What should I check?
Answer:
Start with the most common and simple causes:

1. Power Supply Check:
   - Ensure the power cable is firmly connected to both the computer and wall outlet
   - Try a different power outlet to rule out circuit problems
   - If using a power strip, make sure it's turned on and working with another device

2. If still no response:
   - Disconnect all external devices (except monitor, keyboard, mouse)
   - Press and hold the power button for 30 seconds, then try turning it on again
   - Listen for any beeps or fan noises which indicate power but no display

3. If still not working:
   - Check if the monitor is receiving power (power light on)
   - Try connecting the monitor to a different computer to verify it works
   - Inspect for any blown capacitors or damage on the motherboard

4. Advanced checks:
   - Reset CMOS by removing the motherboard battery for 1 minute
   - Test with a known-working power supply if available
   - If you hear beeps, count the pattern to identify the error code

Question: My WiFi keeps disconnecting. How can I fix it?
Answer:
Try these steps in order, testing after each one:

1. Basic troubleshooting:
   - Restart your router and modem (unplug for 30 seconds, then plug back in)
   - Move closer to your router to check if signal strength is the issue
   - Disconnect other devices to reduce network congestion

2. If still disconnecting:
   - Check for interference from microwaves, Bluetooth devices, or cordless phones
   - Change your router's channel in the admin settings
   - Update your router's firmware to the latest version

3. On your device:
   - Update your WiFi adapter drivers
   - Disable power management for your WiFi adapter in device settings
   - Forget the network and reconnect with the password

4. If problems persist:
   - Reset your router to factory settings
   - Check for overheating issues with your router
   - Consider upgrading your router if it's more than 5 years old"""
} 