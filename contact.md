---
title: Contact
---
### Contact Me
	
You can find me on Twitter at [@drgarybennett](https://www.twitter.com/drgarybennett) or email me using the form below.

<form id="contactform" method="POST">
<!--    <input type="text" name="name" placeholder="Your name">
    <input type="email" name="_replyto" placeholder="Your email">
    <input type="hidden" name="_subject" value="Website contact" />
    <textarea name="message" placeholder="Your message"></textarea>
    <input type="text" name="_gotcha" style="display:none" />
    <input type="submit" value="Send"> -->

	<div class="contain">
		<div class="split">
			<label for="first-name">First Name</label>
			<input type="text" name="first-name" id="first-name" />
		</div>
		<div class="split">
			<label for="surname">Last Name</label>
			<input type="text" name="surname" id="surname" />
		</div>
	</div>

	<div class="contain">
		<div class="split">
			<label for="email">Email Address</label>
			<input type="email" name="email" id="email" required />
		</div>

		<div class="split">
			<label for="subject">Subject</label>
			<select id="subject" name="subject">
				<option value="Inquiry">Inquiry</option>
				<option value="suggestion">Feedback</option>
				<option value="press">Press</option>
				<option value="other">Other</option>
			</select>
		</div>
	</div>

	<label for="message">Message</label>
	<textarea name="message" id="message"></textarea>
	<input type="hidden" name="_next" value="http://drgarybennett.com/contact-success/" />
	<input type="submit" value="Send Message" />
	
	</form>
<script>
    var contactform =  document.getElementById('contactform');
    contactform.setAttribute('action', '//formspree.io/' + 'gary' + '@' + 'bennettlab' + '.' + 'org');
</script>
