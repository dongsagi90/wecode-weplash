import time
import uuid
import json
from PIL              import Image
from urllib.request   import urlopen
from django.views     import View
from django.http      import JsonResponse
from django.db.models import Prefetch, F
from django.db.models import Q, Count
from auth             import login_check

from .models          import (
    HashTag,
    Photo,
    BackGroundColor
)
from account.models   import (
    User,
    Collection,
    Like,
    Follow
)

class RelatedPhotoView(View):
    PHOTO_LIMIT = 20

    def get(self, request, photo_id):
        try:
            photo = Photo.objects.get(id=photo_id)
            related_tags = list(HashTag.objects.filter(photo__id = photo_id).values_list('name', flat=True))
            photo.views = F('views') +1
            photo.save()
            photos = Photo.objects.filter(hashtag__name__in = related_tags).exclude(id=photo_id).prefetch_related(
                "user",
                "collection",
                "photocollection_set",
                "like_set"
            ).distinct()
            result = [{	
                "id"                 : photo.id,	           
                "image"              : photo.image,	            
                "location"           : photo.location,	                
                "user_first_name"    : photo.user.first_name,	                
                "user_last_name"     : photo.user.last_name,	               
                "user_name"          : photo.user.user_name,	                
                "user_profile_image" : photo.user.profile_image	            
            } for photo in photos[:self.PHOTO_LIMIT]]	

            result = [{
                "id"                 : photo.id,
            	"image"              : photo.image,
                "location"           : photo.location,
                "user_first_name"    : photo.user.first_name,
                "user_last_name"     : photo.user.last_name,
                "user_name"          : photo.user.user_name,
                "user_profile_image" : photo.user.profile_image,
                "user_like"          : photo.like_set.filter(user=User.objects.filter(id=user_id).first(), status=True).exists(),
                "user_collection"    : photo.photocollection_set.filter(
                    collection = Collection.objects.filter(
                        user = User.objects.filter(id=user_id).first()
                    ).first(),
                    photo = photo
                ).exists()
            } for photo in photos[:self.PHOTO_LIMIT]]

            return JsonResponse({"tags" : related_tags, "data" : result}, status=200)
        except Photo.DoesNotExist:
            return JsonResponse({'message' : 'NON_EXSITING_PHOTO'}, status=401)
        except ValueError:
            return JsonResponse({"message" : "INVALID_PHOTO"}, status=400)

class RelatedCollectionView(View):
    PHOTO_LIMIT = 20
    @login_check
    def get(self, request, user_id, photo_id):
        try:
            if Photo.objects.filter(id=photo_id).exists():
                collections = Collection.objects.filter(
                    photocollection__photo__id = photo_id
                ).exclude(user=User.objects.get(user_name='weplash')).prefetch_related(
                    Prefetch("photo_set"),
                    Prefetch("photo_set__hashtag")
                )

                result = [{
                    "id"              : collection.id,
                    "image"           : [photo.image for photo in collection.photo_set.all()[:self.LIMIT_NUM]],
                    "name"            : collection.name,
                    "photos_number"   : collection.photo_set.all().count(),
                    "user_first_name" : collection.user.first_name,
                    "user_last_name"  : collection.user.last_name,
                    'tags'            : [tag.name for tag in collection.photo_set.filter().first().hashtag.all()[:self.LIMIT_NUM]]
                } for collection in collections]

                return JsonResponse({'data' : result}, status=200)
            return JsonResponse({"message" : "NON_EXISTING_PHOTO"}, status=401)
        except ValueError:
            return JsonResponse({"message" : "INVALID_PHOTO"}, status=400)

class PhotoView(View):
    @login_check
    def get(self, request, user_id):
        try:
            query = Q()
            offset = int(request.GET.get('offset', 0))
            limit = int(request.GET.get('limit', 20))
            category = request.GET.get('category',None)
            user = request.GET.get('user',None)
            user_category = request.GET.get('user_category',None)
            hashtag = request.GET.get('search',None)

            if category:
                query.add(Q(collection = Collection.objects.get(
                    user = User.objects.get(user_name='weplash'),
                    name = category
                )),query.AND)
                
            elif user:
                if user_category == 'photos':
                    query.add(Q(user = User.objects.get(
                        user_name = user
                    )),query.AND)
                elif user_category == 'likes':
                    query.add(Q(like__user = User.objects.get(
                        user_name = user
                    )),query.AND)
                else:
                    query.add(Q(collection__user = User.objects.get(
                        user_name = user
                    ), collection__name = user_category),query.AND)
            elif hashtag:
                query.add(Q(hashtag = HashTag.objects.get(
                    name = hashtag
                )),query.AND)

            photos = Photo.objects.filter(query).prefetch_related("user")
            data = [{
                "id"                 : photo.id,
                "image"              : photo.image,
                "location"           : photo.location,
                "user_first_name"    : photo.user.first_name,
                "user_last_name"     : photo.user.last_name,
                "user_profile_image" : photo.user.profile_image,
                "user_name"          : photo.user.user_name,
                "width"              : photo.width,
                "height"             : photo.height,               
            } for photo in photos[offset*limit:(offset+1)*limit]]

            return JsonResponse({"data":data},status=200)
        
        except ValueError:
            return JsonResponse({"message":"VALUE_ERROR"},status=400)
        except KeyError:
            return JsonResponse({"message":"KEY_ERROR"},status=400)

class FollowsView(View):
    @login_check
    def get(self,request,user_id):
        if User.objects.filter(id = user_id).exists():
            Photo.objects.filter(user__followee__from_user_id=user_id)

            
            # from_user = User.objects.get(following__followee__from_user= follow,following__follower__status = True)
            # photo = Photo.objects.get(user_id = from_user).prefetch_related("user")
        
        data=[{
            "id"                 : photo.id,
            "image"              : photo.image,
            "location"           : photo.location,
            "user_first_name"    : photo.user.first_name,
            "user_last_name"     : photo.user.last_name,
            "user_profile_image" : photo.user.profile_image,
            "user_name"          : photo.user.user_name,
            "width"              : photo.width,
            "height"             : photo.height
        }]

        return JsonResponse({"data":data},status=200)



class BackgraundView(View):
    def get(self,request, collection_name):
        try:
            query = Q()
            offset = int(request.GET.get('offset', 0))
            limit = int(request.GET.get('limit', 20))
            category = request.GET.get('category',None)
            user = request.GET.get('user',None)
            user_category = request.GET.get('user_category',None)
            hashtag = request.GET.get('search',None)

            if category:
                query.add(Q(collection = Collection.objects.get(
                    user = User.objects.get(user_name='weplash'),
                    name = category
                )),query.AND)
            elif user:
                if user_category == 'photos':
                    query.add(Q(user = User.objects.get(
                        user_name = user
                    )),query.AND)
                elif user_category == 'likes':
                    query.add(Q(like__user = User.objects.get(
                        user_name = user
                    )),query.AND)
                else:
                    query.add(Q(collection__user = User.objects.get(
                        user_name = user
                    ), collection__name = user_category),query.AND)
            elif hashtag:
                query.add(Q(hashtag = HashTag.objects.get(
                    name = hashtag
                )),query.AND)
            photos = Photo.objects.filter(query).prefetch_related("user","background_color")
            data = [{
                "id"                : photo.id,
                "background_color"  : photo.background_color.name,
                "width"             : photo.width,
                "height"            : photo.height
            }for photo in photos[offset*limit:(offset+1)*limit]]
            return JsonResponse({"data":data},status=200)

        except ValueError:
            return JsonResponse({"message":"VALUE_ERROR"},status=400)
        except KeyError:
            return JsonResponse({"message":"KEY_ERROR"},status=400)

class CollectionMainView(View):
    def get(self,request):
        try:
            category = request.GET.get('category',None)
            collection = Collection.objects.get(name=category, user=User.objects.get(user_name='weplash'))
            user = User.objects.filter(photo__photocollection__collection = Collection.objects.get(user=User.objects.get(user_name='weplash'),name='Nature')).distinct().annotate(count=Count('photo__id'))
            result = [{
                    "collection"      : collection.name,
                    "description"     : collection.description,
                    "contributions"   : collection.photocollection_set.all().aggregate(Count('id'))['id__count'],
                    "topcontributors" : list(user.order_by('-count')[:5].values('id', 'profile_image'))
            }]
            return JsonResponse({"data":result},status=200)
        except Collection.DoesNotExist:
            return JsonResponse({'message' : "NON_EXISTING_COLLECTION"}, status=401)
        except ValueError:
            return JsonResponse({"message":"VALUE_ERROR"},status=400)
        except KeyError:
            return JsonResponse({"message":"KEY_ERROR"},status=400)

class UploadView(View):
    @login_check
    def post(self, request, user_id, user_name):
        try:
            if user_id:
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id = AWS_S3['access_key'],
                    aws_secret_access_key = AWS_S3['secret_access_key']
                )

                url_id = str(uuid.uuid4().int)

                s3_client.upload_fileobj(
                    request.FILES['filename'],
                    'weplash',
                    url_id,
                    ExtraArgs={
                        "ContentType" : request.FILES['filename'].content_type
                    }
                )
                data = request.POST.dict()

                im = Image.open(urlopen(S3_URL+url_id))

                photo = Photo.objects.create(
                    user        = User.objects.get(id=user_id),
                    image       = S3_URL+url_id,
                    location    = data['location'],
                    width       = im.width,
                    height      = im.height
                )
                upload_image.delay(photo.image, data)
                return JsonResponse({'message' : 'SUCCESS'}, status=200)
            return JsonResponse({'message' : 'UNAUTHORIZED'}, status=401)
        except KeyError:
            return JsonResponse({'message' : "KEY_ERROR"}, status=400)
