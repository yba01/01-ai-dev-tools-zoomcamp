from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ChoreForm, OverdueChoreForm
from .models import Chore, Member


def _render_page(request, template_name, context=None):
	members = Member.objects.all()
	selected_member = members.filter(
		pk=request.session.get("selected_member_id")
	).first()
	mode = request.session.get("demo_mode", "organizer")
	page_context = {
		"member_options": [
			{
				"id": member.pk,
				"name": member.name,
				"selected": selected_member is not None
				and member.pk == selected_member.pk,
			}
			for member in members
		],
		"mode": mode,
		"organizer_mode": mode == "organizer",
		"member_mode": mode == "member",
		"selected_member": selected_member,
	}
	page_context.update(context or {})
	return render(request, template_name, page_context)


def home(request):
	chores = Chore.objects.select_related("assignee").all()

	return _render_page(
		request,
		"chores/home.html",
		{
			"chores": chores,
			"open_count": chores.filter(completed_at__isnull=True).count(),
			"overdue_count": sum(chore.is_overdue for chore in chores),
			"complete_count": chores.filter(completed_at__isnull=False).count(),
		},
	)


@require_POST
def switch_mode(request):
	mode = request.POST.get("mode")
	if mode == "organizer":
		request.session["demo_mode"] = "organizer"
		request.session.pop("selected_member_id", None)
		messages.info(request, "Organizer mode")
	elif mode == "member":
		member = Member.objects.filter(pk=request.POST.get("member_id")).first()
		if member is None:
			messages.error(request, "Choose a household member to continue.")
		else:
			request.session["demo_mode"] = "member"
			request.session["selected_member_id"] = member.pk
			messages.info(request, f"Member mode: {member.name}")
	else:
		messages.error(request, "Choose Organizer or Member mode.")
	return redirect("chores:home")


def create_chore(request):
	if request.session.get("demo_mode", "organizer") != "organizer":
		messages.error(request, "Switch to Organizer mode to manage chores.")
		return redirect("chores:home")

	form = ChoreForm(request.POST or None, initial={"due_date": timezone.localdate()})
	if request.method == "POST" and form.is_valid():
		chore = form.save()
		messages.success(request, f"{chore.title} was added to the list.")
		return redirect("chores:home")

	return _render_page(
		request,
		"chores/chore_form.html",
		{"form": form, "heading": "Add a chore", "submit_label": "Add chore"},
	)


@require_POST
def complete_chore(request, pk):
	if (
		request.session.get("demo_mode") != "member"
		or not request.session.get("selected_member_id")
	):
		messages.error(request, "Choose a member in Member mode to complete chores.")
		return redirect("chores:home")

	chore = get_object_or_404(Chore, pk=pk)
	if chore.completed_at is None:
		chore.completed_at = timezone.now()
		chore.save(update_fields=["completed_at"])
		messages.success(request, f"{chore.title} marked complete.")
	else:
		messages.info(request, f"{chore.title} is already complete.")
	return redirect("chores:home")


def review_overdue_chore(request, pk):
	if request.session.get("demo_mode", "organizer") != "organizer":
		messages.error(request, "Switch to Organizer mode to update overdue chores.")
		return redirect("chores:home")

	chore = get_object_or_404(Chore, pk=pk)
	if not chore.is_overdue:
		messages.info(request, "Only overdue chores can be rescheduled here.")
		return redirect("chores:home")

	form = OverdueChoreForm(request.POST or None, instance=chore)
	if request.method == "POST" and form.is_valid():
		updated_chore = form.save()
		messages.success(request, f"{updated_chore.title} was updated.")
		return redirect("chores:home")

	return _render_page(
		request,
		"chores/chore_form.html",
		{
			"form": form,
			"heading": "Review overdue chore",
			"submit_label": "Save changes",
			"chore": chore,
		},
	)
