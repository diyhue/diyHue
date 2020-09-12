from flask import Blueprint,render_template

error_pages = Blueprint('error_pages',__name__)

@error_pages.app_errorhandler(404)
def error_404(error):
    '''
    Error for pages not found.
    '''
    # Notice how we return a tuple!
    return render_template('page-404.html'), 404

@error_pages.app_errorhandler(500)
def error_500(error):
    '''
    Error for trying to access something which is forbidden.
    Such as trying to update someone else's blog post.
    '''
    # Notice how we return a tuple!
    return render_template('page-500.html'), 500
