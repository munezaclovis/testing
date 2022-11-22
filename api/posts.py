from flask import jsonify, request, g, abort

from api import api
from db.shared import db
from db.models.user_post import UserPost
from db.models.post import Post
from db.models.user import User

from db.utils import row_to_dict, rows_to_list
from middlewares import auth_required


@api.post("/posts")
@auth_required
def posts():
    # validation
    user = g.get("user")
    if user is None:
        return abort(401)

    data = request.get_json(force=True)
    text = data.get("text", None)
    tags = data.get("tags", None)
    if text is None:
        return jsonify({"error": "Must provide text for the new post"}), 400

    # Create new post
    post_values = {"text": text}
    if tags:
        post_values["tags"] = tags

    post = Post(**post_values)
    db.session.add(post)
    db.session.commit()

    user_post = UserPost(user_id=user.id, post_id=post.id)
    db.session.add(user_post)
    db.session.commit()

    return row_to_dict(post), 200

@api.get("/posts")
@auth_required
def get():
    # validation
    user = g.get("user")
    if user is None:
        return abort(401)
    
       
    authorIds = request.args.get('authorIds', type=str)
    sortBy = request.args.get("sortBy", default="id")
    direction = request.args.get("direction", default="asc")
    if authorIds is None or authorIds == "":
        return jsonify({"error": "Must provide atleast one valid author's id"}), 400
    if sortBy != None and not hasattr(Post, sortBy):
        return jsonify({"error": f"sort option \"{sortBy}\" does not exist"}), 400
    if direction != "asc" and direction != "desc":
        return jsonify({"error": f"direction option \"{direction}\" is invalid"}), 400
    try:
        authorIdArr = list(map(lambda x: int(x), authorIds.strip().strip(",").split(",")))
    except ValueError:
        return jsonify({"error": "Must provide only integer author's id"}), 400
        
    return jsonify({"posts" :rows_to_list(Post.get_posts_by_multiple_user_ids(authorIdArr, sortBy=sortBy, direction=direction))}), 200

@api.patch("/posts/<int:postId>")
@auth_required
def patch(postId):
    # validation
    user = g.get("user")
    if user is None:
        return abort(401)
    
    data = request.get_json(force=True)
    authorIds = data.get("authorIds", None)
    tags = data.get("tags", None)
    text = data.get("text", None)
    try:    
        post = Post.find(postId)
        user_posts = UserPost.query.filter_by(post_id = postId)
        if tags != None: post.tags = tags
        if text != None: post.text = text
        if authorIds != None: 
            users = User.query.filter(User.id.in_(authorIds)).all()
            UserPost.query.filter_by(post_id = postId).delete()
            db.session.commit()
            new_user_posts = []
            for user in users:
                new_user_posts.append(UserPost(user_id=user.id, post_id=postId))
            db.session.add_all(new_user_posts)
            db.session.commit()
    except Exception:
        return jsonify({"error": "Post does not exist"}), 404
    new_post = row_to_dict(post)
    if authorIds != None:
        new_post.update({"authorIds" : [user.id for user in users]})
    else: 
        new_post.update({"authorIds": [user_post.user_id for user_post in user_posts]})
    return jsonify({"post": new_post}), 200