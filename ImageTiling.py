def convertPoints(anno):
    '''
    :param anno:
    :return points:
    :rtype list of lists:
    
    Helper function to convert the X and Y coordinates to the polygon format of XYXY_ABS
    '''
    points = [[]]
                    
    for x_coordinate in range(0,len(anno["all_points_x"]),2):
        points.append([anno["all_points_x"][x_coordinate],anno["all_points_y"][x_coordinate]])
    
    # remove empyt lists from the list of points
    points = [x for x in points if x]
    
    return points



def intersectBoundingBox(points,xmin,ymin,xmax,ymax):
    '''
    :param points:
    :param xmin:
    :param ymin:
    :param xmax:
    :param ymax:
    :rtype list:
    Helper function to intersect the bounding box of the tile with the points in the annotated polygon
    
    '''
  
  
    converted_points = []

    for p in points:
        if p[0]>=xmin and p[0]<=xmax and p[1]>=ymin and p[1]<=ymax:
            p[0]=p[0]-xmin
            p[1]=p[1]-ymin
            converted_points.append(p)
    
    #print(converted_points)

    return converted_points



def readAnnotation(img_dir):
    '''
    :param img_dir:
    :return list of dictionaries:

    '''
    anno_file=os.path.join(img_dir,"regiondata.csv")
    annotab=pd.read_csv(anno_file,delimiter=",")
    files=annotab['filename'].unique()



    return annotab, files

def readImage(img_dir,filename):
    '''
    :param img_dir:
    :param filename:
    :return image:
    '''
    img_file=os.path.join(img_dir,filename)
    img=cv2.imread(img_file)
    height = img.shape[0]
    width = img.shape[1]
    
    # padd the image to be divisible by 512
    # padd the image
    pad_h=(512 - (height % 512)) % 512
    pad_w=(512 - (width % 512)) % 512
    # pad the image
    img=cv2.copyMakeBorder(img,0,pad_h,0,pad_w,cv2.BORDER_CONSTANT,value=[0,0,0])



    return img

def tileImage(img):
    '''
    :param img:
    :return list of coordinates:
    :rtype list:

    Objective: output a list of coordinates for the bounding boxes of the tiles

    '''
    tiles=[[]]
    for i in range(0,img.shape[0],512):
            for j in range(0,img.shape[1],512):
                #print(i,j)
                tile=img[i:i+512,j:j+512]
                xmin=j
                ymin=i
                xmax=j+512
                ymax=i+512
                tiles[0].append([xmin,ymin,xmax,ymax])
                

    return tiles

def IntersectSegmentations(img_dir,output_dir, tiles, img, annotab, file):
    '''
    :param tiles:
    :paramtype list:
    :param img:
    :paramtype numpy array:
    :param annotab:
    :paramtype pandas dataframe:
    :param files:
    :paramtype list:
    :return dataset_dicts:
    :rtype list:

    Objective: iterate over each of the segmentations in the image and intersect them with the tile bounding boxes
    '''
    filename=os.path.join(img_dir,file)
    record = {}
    # iterate over the tile coordinates
    for tile in tiles[0]:
        
        # get the coordinate over the tile image
        xmin=tile[0]
        ymin=tile[1]
        xmax=tile[2]
        ymax=tile[3]
        
        #print(xmin,ymin,xmax,ymax)
        #subset the image to the tile coordinates
        subimg=img[xmin:xmax,ymin:ymax]

        # make a tile id using the UUID
        uid = str(uuid.uuid4())

        # write the image tile to a file using the UID as the name
        #cv2.imwrite(os.path.join(output_dir,uid+'.jpg'),subimg)

        # begin building the record by adding the information for the COCO dataset
        record["filename"] = uid + '.jpg'
        record["height"] = 512
        record["width"] = 512
        # make an empty list of objects for record annotation
        record["annotations"] = []
        
        subtab = annotab[annotab['filename'] == file]
        
        for anno_i in range(subtab.shape[0]):
            
            tab_rec=subtab.iloc[anno_i]
            
            # get the catagory id
            category_id=classes.index(tab_rec['region_attributes'])
            # convert the category id to the class name by using the classes array
            className=classes[category_id]
            anno=json.loads(tab_rec["region_shape_attributes"])
            if len(anno)==0:
                continue
            #print(anno)

            points=convertPoints(anno)
            # this is the problem line
            converted_points=intersectBoundingBox(points,xmin,ymin,xmax,ymax)
            
            if len(converted_points) > 0:
                Sxmin=min(converted_points,key=lambda x:x[0])[0]
                Symin=min(converted_points,key=lambda x:x[1])[1]
                Sxmax=max(converted_points,key=lambda x:x[0])[0]
                Symax=max(converted_points,key=lambda x:x[1])[1]
                Segbbox = [Sxmin,Symin,Sxmax,Symax]

                obj = {
                    'original_file': filename,
                    "tile_coordinates": [xmin,ymin,xmax,ymax],
                    "image_id": uid,
                    'file_name': uid + '.jpg',
                    'height': 512,
                    'width': 512,
                    "category_id": className,
                    "bbox": Segbbox,
                    "segmentation": converted_points,
                    "bbox_mode": 'BoxMode.XYXY_ABS',
                    "iscrowd":0,
                    }
                #print(obj)

                # append the obj to the record
                if record["annotations"] == []:
                    record["annotations"].append(obj)
    return record


            
# Error: overwriting all of the previous tiles
# TODO: Check why the the only tile coordinates being added to the list are the last tile in the list
# possible error spots: line 125... am I only iterating over the one tile?, line 152: do I need to annotate 
# over all of the annotated strcutures in each line? Add one more iteration?


# RUNNER
annotab, files = readAnnotation(img_dir)

# make a list of all the points that intersect tile of an image and append each record to the list
dataset_dicts = []
for stained_image in files:
    img = readImage(img_dir,stained_image)
    tiles = tileImage(img)
    record = IntersectSegmentations(img_dir,output_dir, tiles, img, annotab, stained_image)
    dataset_dicts.append(record)
