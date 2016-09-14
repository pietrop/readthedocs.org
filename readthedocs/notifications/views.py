from django.views.generic import FormView
from django.contrib import admin, messages
from django.http import HttpResponseRedirect

from .forms import SendNotificationForm


class SendNotificationView(FormView):

    """Form view for sending notifications to users from admin pages

    Accepts the following additional parameters:

    queryset
        The queryset to use to determine the users to send emails to

    :cvar action_name: Name of the action to pass to the form template,
                       determines the action to pass back to the admin view
    :cvar notification_classes: List of :py:class:`Notification` classes to
                                display in the form
    :cvar email_context_object_name: Object variable name in templates
    :ivar email_context_data: Addition context data to pass to the templates
    """

    form_class = SendNotificationForm
    template_name = 'core/send_email_form.html'
    action_name = 'send_email'
    notification_classes = []
    email_context_object_name = 'object'
    email_context_data = None

    def get_form_kwargs(self):
        """Override form kwargs based on input fields

        The admin posts to this view initially, so detect the send button on
        form post variables. Drop additional fields if we see the send button.
        """
        kwargs = super(SendNotificationView, self).get_form_kwargs()
        kwargs['notification_classes'] = self.notification_classes
        if 'send' not in self.request.POST:
            kwargs.pop('data', None)
            kwargs.pop('files', None)
        return kwargs

    def get_initial(self):
        """Add selected ids to initial form data"""
        initial = super(SendNotificationView, self).get_initial()
        initial['_selected_action'] = self.request.POST.getlist(
            admin.ACTION_CHECKBOX_NAME)
        return initial

    def form_valid(self, form):
        """If form is valid, send emails to selected recipients

        This treats the body field as a string template, so full template tags
        are allowed in the field.  The object will be available in the template
        as the variable specified by the ``email_context_object_name`` class
        variable.
        """
        count = 0
        notification_cls = form.cleaned_data['source']
        for obj in self.get_queryset().all():
            for recipient in self.get_object_recipients(obj):
                notification = notification_cls(object=obj,
                                                request=self.request,
                                                user=recipient)
                notification.send()
                count += 1
        if count == 0:
            self.message_user("No recipients to send to", level=messages.ERROR)
        else:
            self.message_user("Queued {0} messages".format(count))
        return HttpResponseRedirect(self.request.get_full_path())

    def get_object_recipients(self, obj):
        """An iterator for each recipient address for an object

        This allows for non-User querysets to pass back a list of users to send
        to. By default, assume we're working with :py:class:`User` objects.
        """
        yield obj

    def get_queryset(self):
        return self.kwargs.get('queryset')

    def get_context_data(self, **kwargs):
        """Return queryset in context"""
        context = super(SendNotificationView, self).get_context_data(**kwargs)
        recipients = []
        for obj in self.get_queryset().all():
            recipients.extend(self.get_object_recipients(obj))
        context['recipients'] = recipients
        context['action_name'] = self.action_name
        return context

    def message_user(self, message, level=messages.INFO, extra_tags='',
                     fail_silently=False):
        """Implementation of :py:meth:`django.contrib.admin.options.ModelAdmin.message_user`

        Send message through messages framework
        """
        # TODO generalize this or check if implementation in ModelAdmin is
        # useable here
        messages.add_message(self.request, level, message, extra_tags=extra_tags,
                             fail_silently=fail_silently)
