from micolog_plugin import *
import logging,re
from google.appengine.api import mail
from model import *
from google.appengine.api import users

SBODY='''New comment on your post "%(title)s"
Author : %(author)s
E-mail : %(email)s
URL	: %(weburl)s
Comment:
%(content)s
You can see all comments on this post here:
%(commenturl)s
'''

BBODY='''Hi~ New reference on your comment for post "%(title)s"
Author : %(author)s
URL	: %(weburl)s
Comment:
%(content)s
You can see all comments on this post here:
%(commenturl)s
'''		

class sys_plugin(Plugin):
	def __init__(self):
		Plugin.__init__(self,__file__)
		self.author="xuming"
		self.authoruri="http://xuming.net"
		self.uri="http://xuming.net"
		self.description="System plugin for micolog"
		self.name="Sys Plugin"
		self.version="0.2"
		self.blocklist=OptionSet.getValue("sys_plugin_blocklist",default="")
		self.register_filter('head',self.head)
		self.register_filter('footer',self.footer)
		self.register_urlmap('sys_plugin/setup',self.setup)
		self.register_action('pre_comment',self.pre_comment)
		self.register_action('save_comment',self.save_comment)
		self.sbody=OptionSet.getValue('sys_plugin_sbody',SBODY)
		self.bbody=OptionSet.getValue('sys_plugin_bbody',BBODY)




	def head(self,content,blog=None,*arg1,**arg2):
		content=content+'<meta name="generator" content="Micolog %s" />'%blog.version
		return content

	def footer(self,content,blog=None,*arg1,**arg2):

		return content+'<!--Powered by micolog %s-->'%blog.version

	def setup(self,page=None,*arg1,**arg2):
		if not page.is_login:
			page.redirect(users.create_login_url(page.request.uri))
		tempstr='''blocklist:
			<form action="" method="post">
			<p>
			<textarea name="ta_list" style="width:400px;height:300px">%s</textarea>
			</p>
			<input type="submit" value="submit">
			</form>'''
		if page.request.method=='GET':
			page.render2('views/admin/base.html',{'content':tempstr%self.blocklist})
		else:
			self.blocklist=page.param("ta_list")
			OptionSet.setValue("sys_plugin_blocklist",self.blocklist)
			page.render2('views/admin/base.html',{'content':tempstr%self.blocklist})

	def get(self,page):
		return self.render_content("setup.html",{'self':self})
	
	def post(self,page):
		page.blog.comment_notify_mail=page.parambool('comment_notify_mail')
		page.blog.put()
		return self.get(page)

	def pre_comment(self,comment,*arg1,**arg2):
		for s in self.blocklist.splitlines():
			if comment.content.find(s)>-1:
				raise Exception
	def save_comment(self,comment,*arg1,**arg2):
		if self.blog.comment_notify_mail:
			self.notify(comment)
   	   
	def notify(self,comment):
		
		sbody=self.sbody.decode('utf-8')
		bbody=self.bbody.decode('utf-8')
		
		if self.blog.comment_notify_mail and self.blog.owner and not users.is_current_user_admin() :
			sbody=sbody%{'title':comment.entry.title,
						   'author':comment.author,
						   'weburl':comment.weburl,
						   'email':comment.email,
						   'content':comment.content,
						   'commenturl':comment.entry.fullurl+"#comment-"+str(comment.key().id())
						 }
			mail.send_mail_to_admins(self.blog.owner.email(),'Comments:'+comment.entry.title, sbody,reply_to=comment.email)
			
		#reply comment mail notify
		refers = re.findall(r'#comment-(\d+)', comment.content)
		if len(refers)!=0:
			replyIDs=[int(a) for a in refers]
			commentlist=comment.entry.comments()
			emaillist=[c.email for c in commentlist if c.reply_notify_mail and c.key().id() in replyIDs]
			emaillist = {}.fromkeys(emaillist).keys()
			for refer in emaillist:
				if self.blog.owner and mail.is_email_valid(refer):
						emailbody = bbody%{'title':comment.entry.title,
						   'author':comment.author,
						   'weburl':comment.weburl,
						   'email':comment.email,
						   'content':comment.content,
						   'commenturl':comment.entry.fullurl+"#comment-"+str(comment.key().id())
						 }
						message = mail.EmailMessage(sender = self.blog.owner.email(),subject = 'Comments:'+comment.entry.title)
						message.to = refer
						message.body = emailbody
						message.send()
